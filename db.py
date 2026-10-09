import os
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Fatal: SUPABASE_URL atau SUPABASE_KEY tidak ditemukan di file .env!"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

_PAGE = 1000  # batas baris default PostgREST/Supabase per request


def usage_today() -> date:
    """Tanggal untuk counter kuota Gemini. Kuota harian (RPD) Gemini di-reset tengah
    malam waktu Pasifik, bukan waktu server Anda, jadi counter harus pakai tanggal
    Pasifik supaya hitungannya sejalan dengan reset dari Google."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/Los_Angeles")).date()
    except Exception:
        # Fallback jika tzdata tidak tersedia (mis. Windows): UTC-8 tetap.
        return (datetime.now(timezone.utc) - timedelta(hours=8)).date()


# ---------------------------------------------------------------------------
# user_knowledge
# ---------------------------------------------------------------------------


def save_user_knowledge(
    type: str,
    title: str,
    text_content: str,
    embedding: List[float],
    asset_url: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "type": type,
        "title": title,
        "text_content": text_content,
        "embedding": embedding,
        "asset_url": asset_url,
    }
    response = supabase.table("user_knowledge").insert(payload).execute()
    return response.data[0]


def find_relevant_knowledge(
    job_embedding: List[float], match_threshold: float = 0.7, match_count: int = 3
) -> List[Dict[str, Any]]:
    response = supabase.rpc(
        "match_user_knowledge",
        {
            "query_embedding": job_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count,
        },
    ).execute()
    return response.data


def get_profile_knowledge() -> Optional[Dict[str, Any]]:
    """Dokumen profil utama (type='profile'). Di v2 tidak lagi dipakai ingest.py
    (diganti tracks.py), tapi dipertahankan untuk kompatibilitas."""
    response = (
        supabase.table("user_knowledge")
        .select("text_content, embedding")
        .eq("type", "profile")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]
    return None


def delete_old_knowledge(doc_type: str) -> None:
    supabase.table("user_knowledge").delete().eq("type", doc_type).execute()


# ---------------------------------------------------------------------------
# daily_jobs
# ---------------------------------------------------------------------------


def save_daily_job(
    job_title: str,
    company: str,
    description: str,
    apply_url: str,
    embedding: List[float],
    track: Optional[str] = None,
    source: Optional[str] = None,
    similarity: Optional[float] = None,
    location_note: Optional[str] = None,
    posted_at: Optional[Any] = None,
) -> Dict[str, Any]:
    # processed_date ditetapkan di Python supaya tidak bergantung zona waktu server DB
    payload = {
        "job_title": job_title,
        "company": company,
        "description": description,
        "apply_url": apply_url,
        "embedding": embedding,
        "match_score": 0,
        "ai_reasoning": {},
        "processed_date": date.today().isoformat(),
        "analyzed": False,
        "track": track,
        "source": source,
        "similarity": round(similarity, 4) if similarity is not None else None,
        "location_note": location_note or None,
        "posted_at": posted_at.isoformat() if posted_at else None,
    }
    try:
        response = supabase.table("daily_jobs").insert(payload).execute()
        return response.data[0]
    except Exception as e:
        # v3.9 toleran: bila kolom posted_at belum ada (migration_v3.sql belum
        # dijalankan), coba ulang tanpa kolom itu supaya ingest tidak berhenti.
        if "posted_at" in str(e):
            print("   ⚠️ kolom posted_at belum ada (jalankan migration_v3.sql); coba tanpa kolom.")
            payload.pop("posted_at", None)
            response = supabase.table("daily_jobs").insert(payload).execute()
            return response.data[0]
        raise


def get_unanalyzed_jobs(limit: int) -> List[Dict[str, Any]]:
    """Semua lowongan yang belum dianalisis, dari hari APA PUN (bukan hanya hari ini),
    dengan similarity tertinggi lebih dulu. Versi lama hanya mengambil
    processed_date == hari ini, sehingga job yang tidak sempat dianalisis kemarin
    (kuota habis) tidak pernah diproses lagi."""
    response = (
        supabase.table("daily_jobs")
        .select("*")
        .eq("analyzed", False)
        .order("similarity", desc=True, nullsfirst=False)
        .limit(limit)
        .execute()
    )
    return response.data or []


def update_job_reasoning(
    job_id: int, match_score: int, ai_reasoning: Dict[str, Any]
) -> None:
    supabase.table("daily_jobs").update(
        {"match_score": match_score, "ai_reasoning": ai_reasoning, "analyzed": True}
    ).eq("id", job_id).execute()


def mark_jobs_notified(job_ids: List[int]) -> None:
    if not job_ids:
        return
    supabase.table("daily_jobs").update({"notified": True}).in_("id", job_ids).execute()


def delete_old_jobs(retention_days: int) -> None:
    cutoff = (date.today() - timedelta(days=retention_days)).isoformat()
    supabase.table("daily_jobs").delete().lt("processed_date", cutoff).execute()


# ---------------------------------------------------------------------------
# seen_jobs: memori lintas-run untuk SEMUA lowongan yang sudah pernah dievaluasi
# ---------------------------------------------------------------------------


def load_seen_keys(days: int) -> Set[str]:
    """Kunci lowongan yang sudah pernah dievaluasi (disimpan ATAU ditolak similarity)
    dalam `days` hari terakhir, plus isi daily_jobs (untuk data sebelum migrasi).
    Paginasi dipakai karena Supabase membatasi 1000 baris per request."""
    seen: Set[str] = set()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    start = 0
    while True:
        resp = (
            supabase.table("seen_jobs")
            .select("job_key")
            .gte("last_seen", cutoff)
            .range(start, start + _PAGE - 1)
            .execute()
        )
        rows = resp.data or []
        seen.update(r["job_key"] for r in rows if r.get("job_key"))
        if len(rows) < _PAGE:
            break
        start += _PAGE

    from filters import normalize_url, title_company_key

    start = 0
    while True:
        resp = (
            supabase.table("daily_jobs")
            .select("apply_url, job_title, company")
            .range(start, start + _PAGE - 1)
            .execute()
        )
        rows = resp.data or []
        for r in rows:
            if r.get("apply_url"):
                seen.add(normalize_url(r["apply_url"]))
            seen.add(title_company_key(r.get("job_title", ""), r.get("company", "")))
        if len(rows) < _PAGE:
            break
        start += _PAGE
    return seen


def remember_jobs(rows: List[Dict[str, Any]]) -> None:
    """rows: [{job_key, outcome, similarity}]. Upsert, last_seen diperbarui."""
    if not rows:
        return
    today = date.today().isoformat()
    payload = [
        {
            "job_key": r["job_key"],
            "outcome": r.get("outcome"),
            "similarity": (
                round(r["similarity"], 4) if r.get("similarity") is not None else None
            ),
            "last_seen": today,
        }
        for r in rows
    ]
    supabase.table("seen_jobs").upsert(payload, on_conflict="job_key").execute()


def delete_old_seen(days: int) -> None:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    supabase.table("seen_jobs").delete().lt("last_seen", cutoff).execute()


# ---------------------------------------------------------------------------
# track_profiles: cache embedding tiap bidang (di-embed ulang hanya bila teks berubah)
# ---------------------------------------------------------------------------


def get_track_profiles() -> Dict[str, Dict[str, Any]]:
    resp = (
        supabase.table("track_profiles").select("name, text_hash, embedding").execute()
    )
    return {r["name"]: r for r in (resp.data or [])}


def upsert_track_profile(name: str, text_hash: str, embedding: List[float]) -> None:
    supabase.table("track_profiles").upsert(
        {"name": name, "text_hash": text_hash, "embedding": embedding},
        on_conflict="name",
    ).execute()


# ---------------------------------------------------------------------------
# Usage counter (proteksi RPD Gemini lintas-run), tanggal mengikuti zona Pasifik
# Tabel `api_usage` sudah ada dari versi sebelumnya.
# ---------------------------------------------------------------------------


def get_today_usage() -> Dict[str, int]:
    today_str = usage_today().isoformat()
    response = (
        supabase.table("api_usage").select("*").eq("usage_date", today_str).execute()
    )
    if response.data:
        return response.data[0]
    return {"usage_date": today_str, "embedding_calls": 0, "reasoning_calls": 0}


def increment_usage(api_type: str, new_total: int) -> None:
    """Simpan nilai counter TERBARU (absolut) untuk hari ini, bukan delta."""
    today_str = usage_today().isoformat()
    payload = {"usage_date": today_str, f"{api_type}_calls": new_total}
    supabase.table("api_usage").upsert(payload, on_conflict="usage_date").execute()


if __name__ == "__main__":
    print("Mengecek koneksi ke Supabase...")
    try:
        supabase.table("user_knowledge").select("id").limit(1).execute()
        print("✅ user_knowledge dapat diakses.")
        for tbl in ("seen_jobs", "track_profiles", "api_usage"):
            try:
                supabase.table(tbl).select("*").limit(1).execute()
                print(f"✅ tabel {tbl} OK.")
            except Exception as e:
                print(
                    f"❌ tabel {tbl} bermasalah (sudah jalankan migration_v2.sql?): {e}"
                )
    except Exception as e:
        print(f"❌ Gagal koneksi: {e}")
