import os
import json
import html
import time
import requests
from datetime import date
from typing import Any, Dict, List
from dotenv import load_dotenv

from db import supabase, mark_jobs_notified
from tracks import TRACKS

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_JOBS_TO_NOTIFY = int(os.getenv("MAX_JOBS_TO_NOTIFY", "15"))
# Lowongan di bawah skor ini tidak dikirim. V3: 60 -> 50 supaya tidak sunyi berminggu-
# minggu; kualitas tetap dijaga reasoning. Angka bisa dioverride lewat env/secrets.
MIN_NOTIFY_SCORE = int(os.getenv("MIN_NOTIFY_SCORE", "50"))
# Batas Telegram 4096 karakter; sisakan ruang untuk header/footer.
TELEGRAM_SAFE_LIMIT = 3800

REGION_TAGS = {
    "worldwide": "🌍 Worldwide",
    "apac_ok": "🌏 APAC OK",
    "restricted": "⛔ Region terbatas",
    "unclear": "❔ Region belum jelas",
}


def esc(text: Any) -> str:
    return html.escape(str(text)) if text else ""


def clip(text: Any, n: int = 150) -> str:
    s = esc(text)
    return s if len(s) <= n else s[: n - 3] + "..."


def send_telegram_message(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Konfigurasi Telegram belum diisi di .env. Melewati pengiriman.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = None
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Pesan berhasil dikirim ke Telegram!")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Gagal mengirim ke Telegram: {e}")
        if response is not None:
            print(f"🔍 Detail: {response.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengirim ke Telegram (koneksi/timeout): {e}")
        return False


def build_job_block(index: int, job: Dict[str, Any]) -> str:
    score = job["match_score"]
    reasoning = job.get("ai_reasoning") or {}
    if isinstance(reasoning, str):
        try:
            reasoning = json.loads(reasoning)
        except Exception:
            reasoning = {}

    reasons = reasoning.get("match_reasons") or ["Tidak ada alasan spesifik."]
    if isinstance(reasons, str):
        reasons = [reasons]
    talking = reasoning.get("interview_talking_points") or []
    emoji = "🔥" if score >= 80 else "✅" if score >= 60 else "⚠️"

    track = TRACKS.get(job.get("track") or "", {})
    track_tag = f"{track.get('emoji', '')} {track.get('label', '')}".strip()
    region = REGION_TAGS.get(reasoning.get("region_eligibility"), "")

    lines = [f"{emoji} <b>{index}. {clip(job['job_title'], 100)}</b>"]
    lines.append(
        f"   🏢 {clip(job['company'], 60)}"
        + (f" | {esc(track_tag)}" if track_tag else "")
    )
    lines.append(f"   📊 <b>Skor:</b> {score}/100" + (f" | {region}" if region else ""))
    lines.append("   💡 <b>Mengapa Cocok:</b>")
    for r in reasons[:2]:
        lines.append(f"   • {clip(r)}")
    if reasoning.get("cv_angle"):
        lines.append(f"   📝 <b>Angle CV:</b> {clip(reasoning['cv_angle'], 200)}")
    lines.append(
        f"   🎯 <b>Skill Gap:</b> {clip(reasoning.get('skill_gap', 'Tidak teridentifikasi.'))}"
    )
    if isinstance(talking, list) and talking:
        lines.append(f'   🗣️ <b>Talking Point:</b> "{clip(talking[0])}"')
    url = esc(job.get("apply_url", ""))
    lines.append(
        f'   🔗 <a href="{url}">Apply Here</a>' if url else "   🔗 Link tidak tersedia"
    )
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines) + "\n"


def pack_messages(blocks: List[str], header: str, footer: str) -> List[List[int]]:
    """Kelompokkan blok ke beberapa pesan tanpa melewati batas Telegram. Mengembalikan
    daftar grup berisi indeks blok. (Versi lama memakai 3 job tetap per pesan, yang bisa
    melewati 4096 karakter bila URL panjang, dan batch gagal itu diulang selamanya.)"""
    groups: List[List[int]] = []
    current: List[int] = []
    size = len(header) + len(footer)
    for i, b in enumerate(blocks):
        if current and size + len(b) > TELEGRAM_SAFE_LIMIT:
            groups.append(current)
            current, size = [], len(header) + len(footer)
        current.append(i)
        size += len(b)
    if current:
        groups.append(current)
    return groups


def _send_empty_status(today: str):
    """V3: tetap kirim status singkat walau hasil kosong, supaya sunyi tidak misterius.
    Lowongan 'nyaris lolos' ditandai notified agar pesan sama tidak berulang tiap hari."""
    try:
        resp = (
            supabase.table("daily_jobs")
            .select("id, job_title, company, match_score")
            .eq("analyzed", True)
            .eq("notified", False)
            .order("match_score", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            b = rows[0]
            msg = (
                f"📭 <b>AI Career Architect - {today}</b>\n"
                f"Tidak ada lowongan mencapai skor {MIN_NOTIFY_SCORE}.\n"
                f"Terdekat: {clip(b.get('job_title'), 70)}"
                f" ({clip(b.get('company'), 30)}) — skor {b.get('match_score', 0)}.\n"
                f"<i>Bila berhari-hari begini: pertimbangkan turunkan MIN_NOTIFY_SCORE"
                f" atau SIMILARITY_THRESHOLD.</i>"
            )
            if send_telegram_message(msg):
                mark_jobs_notified([b["id"]])
        else:
            send_telegram_message(
                f"📭 <b>AI Career Architect - {today}</b>\n"
                f"Tidak ada lowongan baru selesai dianalisis hari ini (funnel kosong atau ingest tidak jalan)."
            )
    except Exception as e:
        print(f"   ⚠️ Gagal mengirim status kosong: {e}")


def format_and_notify():
    print("🚀 Fase D (v2): Notification Layer...")
    today = date.today().isoformat()

    # Tanpa filter processed_date: job yang baru selesai dianalisis hari ini tapi
    # di-ingest kemarin tetap terkirim.
    response = (
        supabase.table("daily_jobs")
        .select("id, job_title, company, match_score, ai_reasoning, apply_url, track")
        .eq("analyzed", True)
        .eq("notified", False)
        .gte("match_score", MIN_NOTIFY_SCORE)
        .order("match_score", desc=True)
        .limit(MAX_JOBS_TO_NOTIFY)
        .execute()
    )
    top_jobs = response.data or []
    if not top_jobs:
        print(f"⚠️ Tidak ada lowongan baru dengan skor >= {MIN_NOTIFY_SCORE}.")
        _send_empty_status(today)
        return

    blocks = [build_job_block(i, j) for i, j in enumerate(top_jobs, 1)]
    footer = "💡 <i>Tool ini hanya memberi rekomendasi. Review dan apply manual lewat link di atas.</i>"
    groups = pack_messages(blocks, "x" * 220, footer)
    print(f"✅ {len(top_jobs)} lowongan akan dikirim dalam {len(groups)} pesan.")

    for n, idx in enumerate(groups, 1):
        header = (
            f"🎯 <b>AI Career Architect - Daily Match ({n}/{len(groups)})</b>\n"
            f"📅 {today}\n\n"
        )
        message = header + "".join(blocks[i] for i in idx) + footer
        if send_telegram_message(message):
            mark_jobs_notified([top_jobs[i]["id"] for i in idx])
        else:
            print(
                "   ⚠️ Pesan gagal, TIDAK ditandai notified -> dicoba lagi di run berikutnya."
            )
        if n < len(groups):
            time.sleep(1.5)

    print("🎉 Fase D selesai.")


if __name__ == "__main__":
    format_and_notify()
