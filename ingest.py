"""Fase B (v2): ambil lowongan dari banyak sumber, saring murah dulu, rutekan ke
bidang (tracks.py), baru embed & bandingkan dengan profil bidang tersebut.

Pemakaian:
    python ingest.py                         # run normal
    python ingest.py --dry-run               # TANPA embedding & tulis DB; cetak statistik funnel
    python ingest.py --dry-run --tracks=crm_ops,construction
"""

import os
import re
import sys
import json
import time
import hashlib
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

import requests
from dotenv import load_dotenv

from filters import (
    clean_html,
    cosine_similarity,
    is_recent_enough,
    is_scam_risk,
    is_title_excluded,
    job_keys,
    location_verdict,
    requires_other_language,
    route_tracks,
)
from tracks import TRACKS, EXCLUDE_TITLE_TERMS

load_dotenv()

# V3: 0.58 -> 0.52. Corong v2 terlalu sempit (hanya 5 dari 346 lowongan unik yang
# sampai ke tahap embedding). Kualitas akhir tetap dijaga tahap reasoning + skor notifikasi.
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.52"))
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"
MAX_JOBS_TO_EMBED = int(os.getenv("MAX_JOBS_TO_EMBED", "150"))
MAX_JOB_AGE_DAYS = int(os.getenv("MAX_JOB_AGE_DAYS", "21"))
# V3: 2 -> 3 query per bidang (11 bidang aktif = cakupan pencarian lebih luas).
MAX_QUERIES_PER_TRACK = int(os.getenv("MAX_QUERIES_PER_TRACK", "3"))
MIN_DESC_CHARS = int(os.getenv("MIN_DESC_CHARS", "150"))
SEEN_RETENTION_DAYS = int(os.getenv("SEEN_RETENTION_DAYS", "45"))
DISABLED_SOURCES = {
    s.strip().lower() for s in os.getenv("DISABLED_SOURCES", "").split(",") if s.strip()
}

UA = {"User-Agent": "Mozilla/5.0 (compatible; JobHuntBot/2.0; personal use)"}

WWR_FEEDS = [
    "https://weworkremotely.com/remote-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    "https://weworkremotely.com/categories/all-other-remote-jobs.rss",
    # v3.2: feed kategori tambahan — stabil (RSS statis) dan sangat relevan untuk
    # track baru. Management & Finance -> ops_pm/finance_ops; Sales & Marketing ->
    # cs_success/crm_ops/content_ops; Programming & Full-Stack -> ai_automation;
    # Product -> ops_pm. Duplikat antar-feed diurus dedup di process_jobs.
    "https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss",
    "https://weworkremotely.com/categories/remote-sales-and-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def fetch_with_retry(
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = 12,
    max_retries: int = 3,
) -> Optional[requests.Response]:
    merged = {**UA, **(headers or {})}
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=merged, params=params, timeout=timeout)
            if resp.status_code not in (408, 429, 500, 502, 503, 504):
                return resp
            reason = f"HTTP {resp.status_code}"
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            reason = "timeout/koneksi"
        if attempt < max_retries:
            print(
                f"         ⚠️ {reason} (percobaan {attempt}/{max_retries}), tunggu 3 detik..."
            )
            time.sleep(3)
        else:
            print(f"         ⚠️ {reason}, menyerah setelah {max_retries} percobaan.")
    return None


def _json(resp: Optional[requests.Response]) -> Any:
    if resp is None or resp.status_code != 200:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def _job(
    title, company, description, url, source, posted_at=None, location=None
) -> Dict[str, Any]:
    return {
        "title": str(title or "").strip(),
        "company": str(company or "Unknown").strip() or "Unknown",
        "description": clean_html(description),
        "url": str(url or "").strip(),
        "source": source,
        "posted_at": posted_at,
        "location": location,  # field lokasi mentah dari API sumber (str / list / None)
    }


# ---------------------------------------------------------------------------
# Sumber lowongan. Tiap fungsi mengembalikan list dict seragam (lihat _job).
# Field lokasi diambil dari API sumber bila ada: ini penyaring "worldwide" paling andal.
# ---------------------------------------------------------------------------


def fetch_himalayas() -> List[Dict[str, Any]]:
    print("      -> Himalayas...")
    data = _json(fetch_with_retry("https://himalayas.app/jobs/api?limit=30"))
    jobs = [
        _job(
            j.get("title"),
            j.get("companyName"),
            j.get("description"),
            j.get("applicationLink") or j.get("jobUrl"),
            "Himalayas",
            j.get("pubDate"),
            j.get("locationRestrictions"),
        )
        for j in ((data or {}).get("jobs") or [])
    ]
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_jobicy(tag: Optional[str] = None) -> List[Dict[str, Any]]:
    print(f"      -> Jobicy{' [' + tag + ']' if tag else ''}...")
    params = {"count": 30, "geo": "anywhere"}
    if tag:
        params["tag"] = tag
    data = _json(
        fetch_with_retry("https://jobicy.com/api/v2/remote-jobs", params=params)
    )
    jobs = [
        _job(
            j.get("jobTitle"),
            j.get("companyName"),
            j.get("jobDescription"),
            j.get("url"),
            "Jobicy",
            j.get("pubDate"),
            j.get("jobGeo"),
        )
        for j in ((data or {}).get("jobs") or [])
    ]
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_remoteok() -> List[Dict[str, Any]]:
    print("      -> RemoteOK...")
    data = _json(fetch_with_retry("https://remoteok.com/api"))
    jobs = []
    # Elemen pertama RemoteOK hanya legal notice (tanpa "id").
    for j in data or []:
        if not isinstance(j, dict) or not j.get("id"):
            continue
        jobs.append(
            _job(
                j.get("position"),
                j.get("company"),
                j.get("description"),
                j.get("url"),
                "RemoteOK",
                j.get("date"),
                j.get("location"),
            )
        )
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_arbeitnow() -> List[Dict[str, Any]]:
    print("      -> Arbeitnow (remote saja)...")
    data = _json(fetch_with_retry("https://www.arbeitnow.com/api/job-board-api"))
    jobs = [
        _job(
            j.get("title"),
            j.get("company_name"),
            j.get("description"),
            j.get("url"),
            "Arbeitnow",
            j.get("created_at"),
            j.get("location"),
        )
        for j in ((data or {}).get("data") or [])
        if j.get("remote")
    ]
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_remotive(query: str) -> List[Dict[str, Any]]:
    print(f"      -> Remotive [{query}]...")
    data = _json(
        fetch_with_retry(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": 30},
        )
    )
    jobs = [
        _job(
            j.get("title"),
            j.get("company_name"),
            j.get("description"),
            j.get("url"),
            "Remotive",
            j.get("publication_date"),
            j.get("candidate_required_location"),
        )
        for j in ((data or {}).get("jobs") or [])
    ]
    print(f"         {len(jobs)} lowongan.")
    return jobs


# v3.2: RemoteJobs.org DIBUANG — API-nya konsisten membalas HTTP 429 dari IP GitHub
# Actions (2 hari observasi: nol lowongan, hanya membuang waktu retry ±33 panggilan/run).
# Penggantinya: 5 feed kategori We Work Remotely (lihat WWR_FEEDS di atas).


def fetch_weworkremotely() -> List[Dict[str, Any]]:
    """RSS We Work Remotely. Judul berformat 'Perusahaan: Judul', dan ada tag <region>
    (mis. 'Anywhere in the World') yang sangat berguna untuk filter worldwide."""
    print("      -> We Work Remotely (RSS)...")
    jobs = []
    for feed in WWR_FEEDS:
        resp = fetch_with_retry(feed, timeout=15, max_retries=2)
        if not resp or resp.status_code != 200:
            print(f"         ⚠️ feed gagal: {feed}")
            continue
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            print(f"         ⚠️ feed bukan XML valid: {feed}")
            continue
        for item in root.iter("item"):
            raw_title = (item.findtext("title") or "").strip()
            company, sep, title = raw_title.partition(": ")
            if not sep:
                company, title = "Unknown", raw_title
            jobs.append(
                _job(
                    title,
                    company,
                    item.findtext("description"),
                    item.findtext("link"),
                    "WeWorkRemotely",
                    item.findtext("pubDate"),
                    item.findtext("region"),
                )
            )
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_jsearch(query: str) -> List[Dict[str, Any]]:
    if not RAPIDAPI_KEY:
        return []
    print(f"      -> JSearch [{query}] (memakai jatah RapidAPI)...")
    data = _json(
        fetch_with_retry(
            f"https://{RAPIDAPI_HOST}/search-v2",
            headers={"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST},
            params={"query": query, "page": "1", "num_pages": "1"},
        )
    )
    raw = (data or {}).get("data")
    items = (
        raw.get("jobs", [])
        if isinstance(raw, dict)
        else (raw if isinstance(raw, list) else [])
    )
    jobs = [
        _job(
            j.get("job_title"),
            j.get("employer_name"),
            j.get("job_description"),
            j.get("job_apply_link"),
            "JSearch",
            j.get("job_posted_at_datetime_utc"),
        )
        for j in items
    ]
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_remotive_full() -> List[Dict[str, Any]]:
    """Feed penuh Remotive (tanpa kata kunci) — semua lowongan remote terbaru."""
    return fetch_remotive("")


def fetch_workingnomads() -> List[Dict[str, Any]]:
    print("      -> Working Nomads...")
    data = _json(fetch_with_retry("https://www.workingnomads.com/api/exposed_jobs/"))
    jobs = [
        _job(
            j.get("title"),
            j.get("company_name"),
            j.get("description"),
            j.get("url"),
            "WorkingNomads",
            j.get("pub_date"),
            j.get("location"),
        )
        for j in (data if isinstance(data, list) else [])
    ]
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_n8n_community() -> List[Dict[str, Any]]:
    """RSS kategori Jobs di forum komunitas n8n — proyek freelance/kontrak
    n8n & AI automation dari seluruh dunia, sangat relevan untuk track ai_automation."""
    print("      -> n8n Community (RSS)...")
    jobs: List[Dict[str, Any]] = []
    resp = fetch_with_retry(
        "https://community.n8n.io/c/jobs/13.rss", timeout=15, max_retries=2
    )
    if not resp or resp.status_code != 200:
        print("         ⚠️ feed n8n RSS gagal.")
        return jobs
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        print("         ⚠️ n8n RSS bukan XML valid.")
        return jobs
    for item in root.iter("item"):
        jobs.append(
            _job(
                (item.findtext("title") or "").strip(),
                "n8n Community",
                item.findtext("description"),
                item.findtext("link"),
                "n8nCommunity",
                item.findtext("pubDate"),
            )
        )
    print(f"         {len(jobs)} lowongan.")
    return jobs


def fetch_hn_whoshiring() -> List[Dict[str, Any]]:
    """Thread bulanan 'Ask HN: Who is hiring?' via Algolia API (gratis, tanpa key).
    Hanya komentar yang mengandung 'remote' yang diambil. Format umumnya:
    'Company | Location | Full Time | REMOTE | Role | Skills | URL'."""
    print("      -> HN Who's Hiring...")
    meta = _json(
        fetch_with_retry(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"tags": "author_whoishiring,story", "hitsPerPage": 6},
        )
    )
    story = None
    for h in (meta or {}).get("hits", []):
        if "who is hiring" in (h.get("title") or "").lower():
            story = h
            break
    if not story:
        print("         ⚠️ Thread 'Who is hiring?' tidak ditemukan.")
        return []
    data = _json(
        fetch_with_retry(
            f"https://hn.algolia.com/api/v1/items/{story['objectID']}", timeout=30
        )
    )
    jobs: List[Dict[str, Any]] = []
    _NOISE = {"remote", "full time", "part time", "contract", "full-time", "part-time"}
    for c in (data or {}).get("children", []):
        raw = c.get("text") or ""
        if "remote" not in raw.lower():
            continue
        text = clean_html(raw)
        if len(text) < MIN_DESC_CHARS:
            continue
        m = re.search(r"https?://[^\s<\"']+", raw)
        link = m.group(0) if m else f"https://news.ycombinator.com/item?id={c.get('id')}"
        parts = [p.strip() for p in text.split("|") if p.strip()]
        company = parts[0][:60] if parts else "Unknown"
        title = company
        if len(parts) > 1:
            candidates = [
                p
                for p in parts[1:]
                if "http" not in p.lower() and p.strip().lower() not in _NOISE
            ]
            if candidates:
                title = max(candidates, key=len)[:90]
        jobs.append(
            _job(title, company, text, link, "HN WhosHiring", story.get("created_at"), None)
        )
    print(
        f"         {len(jobs)} lowongan remote (thread: {(story.get('title') or '')[:45]})."
    )
    return jobs


def _on(source: str) -> bool:
    return source.lower() not in DISABLED_SOURCES


def fetch_all(tracks: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    print("   [Step 2] Mengambil lowongan dari berbagai sumber...")
    queries: List[str] = []
    for t in tracks.values():
        for q in t.get("queries", [])[:MAX_QUERIES_PER_TRACK]:
            if q not in queries:
                queries.append(q)
    print(f"      -> {len(queries)} query dari {len(tracks)} bidang: {queries}")

    jobs: List[Dict[str, Any]] = []
    # Sumber feed penuh: cukup sekali, penyaringan relevansi terjadi di tahap berikutnya.
    for name, fn in (
        ("himalayas", fetch_himalayas),
        ("jobicy", fetch_jobicy),
        ("remoteok", fetch_remoteok),
        ("arbeitnow", fetch_arbeitnow),
        ("weworkremotely", fetch_weworkremotely),
        ("remotive_full", fetch_remotive_full),
        ("workingnomads", fetch_workingnomads),
        ("n8n_community", fetch_n8n_community),
        ("hn_whoshiring", fetch_hn_whoshiring),
    ):
        if _on(name):
            jobs.extend(fn())

    # Sumber yang menerima pencarian: satu panggilan per query.
    # (v3.2: RemoteJobs.org dihapus dari loop ini.)
    for q in queries:
        if _on("remotive"):
            jobs.extend(fetch_remotive(q))
        if _on("jobicy"):
            jobs.extend(fetch_jobicy(q))
        time.sleep(0.5)  # sopan ke API gratis

    # JSearch (RapidAPI) v3: 2 query ROTASI harian dengan suffix "remote"
    # (syarat mutlak user: 100% remote), bukan lagi hanya fallback saat sumber
    # lain kosong. Kuota: ~2 call/hari ≈ 60/bulan dari 500 free tier.
    if queries and _on("jsearch") and RAPIDAPI_KEY:
        from datetime import date as _date

        n = _date.today().toordinal()
        picks: List[str] = []
        i = n
        while len(picks) < min(2, len(queries)):
            q = queries[i % len(queries)]
            if q not in picks:
                picks.append(q)
            i += 1
        for q in picks:
            jobs.extend(fetch_jsearch(f"{q} remote"))

    print(
        f"      -> Total mentah: {len(jobs)} | per sumber: {dict(Counter(j['source'] for j in jobs))}"
    )
    return jobs


# ---------------------------------------------------------------------------
# Embedding profil bidang (cache di DB, di-embed ulang hanya bila teks berubah)
# ---------------------------------------------------------------------------


def _as_vector(raw: Any) -> List[float]:
    return json.loads(raw) if isinstance(raw, str) else list(raw)


def sync_track_embeddings(tracks: Dict[str, Dict[str, Any]]) -> Dict[str, List[float]]:
    from ai_engine import get_embedding
    from db import get_track_profiles, upsert_track_profile

    print("   [Step 1] Menyiapkan embedding profil tiap bidang...")
    cached = get_track_profiles()
    vectors: Dict[str, List[float]] = {}
    for name, t in tracks.items():
        text_hash = hashlib.sha256(t["profile_text"].encode("utf-8")).hexdigest()[:16]
        row = cached.get(name)
        if row and row.get("text_hash") == text_hash and row.get("embedding"):
            vectors[name] = _as_vector(row["embedding"])
            continue
        print(f"      -> meng-embed ulang bidang '{name}'")
        vec = get_embedding(t["profile_text"])
        upsert_track_profile(name, text_hash, vec)
        vectors[name] = vec
    return vectors


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

FUNNEL_ORDER = [
    "mentah",
    "duplikat_in_run",
    "data_rusak",
    "sudah_pernah_dilihat",
    "deskripsi_pendek",
    "terlalu_lama",
    "judul_dikecualikan",
    "region_terbatas",
    "bahasa_asing",
    "indikasi_scam",
    "tidak_ada_bidang",
    "batas_embed_run",
    "gagal_embedding",
    "similarity_rendah",
    "lolos_dicek_embedding",
    "TERSIMPAN",
]


def process_jobs(
    raw_jobs: List[Dict[str, Any]],
    tracks: Dict[str, Dict[str, Any]],
    track_vecs: Dict[str, List[float]],
    seen: Set[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    funnel: Counter = Counter()
    funnel["mentah"] = len(raw_jobs)
    candidates_by_track: Dict[str, List[str]] = defaultdict(list)
    saved_by_track: Counter = Counter()
    pending_seen: List[Dict[str, Any]] = []
    embedded = 0

    def flush_seen(force: bool = False) -> None:
        nonlocal pending_seen
        if dry_run or not pending_seen or (len(pending_seen) < 40 and not force):
            return
        try:
            from db import remember_jobs

            remember_jobs(pending_seen)
            pending_seen = []
        except Exception as e:
            print(f"         ⚠️ Gagal menyimpan seen_jobs: {e}")

    def remember(job: Dict[str, Any], outcome: str, sim: Optional[float]) -> None:
        for k in job_keys(job):
            pending_seen.append({"job_key": k, "outcome": outcome, "similarity": sim})
        flush_seen()

    # Dedup dalam satu run (lintas sumber)
    unique: Dict[str, Dict[str, Any]] = {}
    for job in raw_jobs:
        if not job["title"]:
            funnel["data_rusak"] += 1
            continue
        key = job_keys(job)[0]
        if key in unique:
            funnel["duplikat_in_run"] += 1
        else:
            unique[key] = job

    print(
        f"\n   [Step 3] Menyaring {len(unique)} lowongan unik "
        f"(batas embedding per-run: {MAX_JOBS_TO_EMBED})..."
    )

    try:
        for job in unique.values():
            if any(k in seen for k in job_keys(job)):
                funnel["sudah_pernah_dilihat"] += 1
                continue
            if len(job["description"]) < MIN_DESC_CHARS:
                funnel["deskripsi_pendek"] += 1
                continue
            if not is_recent_enough(job["posted_at"], MAX_JOB_AGE_DAYS):
                funnel["terlalu_lama"] += 1
                continue
            if is_title_excluded(job["title"], EXCLUDE_TITLE_TERMS):
                funnel["judul_dikecualikan"] += 1
                continue

            text = f"{job['title']} {job['description']}"
            verdict, loc_note = location_verdict(job["location"], text, job["title"])
            if verdict == "restricted":
                funnel["region_terbatas"] += 1
                continue
            # V3: buang lowongan yang mensyaratkan bahasa selain Inggris/Indonesia.
            lang_hit = requires_other_language(text)
            if lang_hit:
                funnel["bahasa_asing"] += 1
                continue
            if is_scam_risk(text):
                funnel["indikasi_scam"] += 1
                continue

            eligible = route_tracks(job["title"], text, tracks)
            if not eligible:
                funnel["tidak_ada_bidang"] += 1
                continue

            funnel["lolos_dicek_embedding"] += 1
            for name, _, _ in eligible:
                candidates_by_track[name].append(
                    f"{job['title'][:60]} ({job['source']})"
                )
            if dry_run:
                continue

            if embedded >= MAX_JOBS_TO_EMBED:
                funnel["batas_embed_run"] += 1
                continue

            from ai_engine import RateBudgetExceeded, get_embedding

            try:
                job_emb = get_embedding(job["description"][:3000])
                embedded += 1
            except RateBudgetExceeded as e:
                print(f"         🛑 {e} Menghentikan embedding untuk run ini.")
                break
            except Exception:
                funnel["gagal_embedding"] += 1
                continue

            sims = {
                n: cosine_similarity(job_emb, track_vecs[n])
                for n, _, _ in eligible
                if n in track_vecs
            }
            if not sims:
                funnel["tidak_ada_bidang"] += 1
                continue
            best = max(sims, key=sims.get)
            threshold = tracks[best].get("threshold") or SIMILARITY_THRESHOLD

            if sims[best] >= threshold:
                try:
                    from db import save_daily_job

                    save_daily_job(
                        job_title=job["title"],
                        company=job["company"],
                        description=job["description"],
                        apply_url=job["url"],
                        embedding=job_emb,
                        track=best,
                        source=job["source"],
                        similarity=sims[best],
                        location_note=loc_note,
                    )
                    funnel["TERSIMPAN"] += 1
                    saved_by_track[best] += 1
                    remember(job, "saved", sims[best])
                    print(
                        f"         ✅ [{best}] {sims[best]:.3f} | {job['title'][:55]} | {job['company'][:25]}"
                    )
                except Exception as e:
                    print(f"         ❌ Gagal simpan DB: {e}")
            else:
                funnel["similarity_rendah"] += 1
                remember(job, "low_similarity", sims[best])
    finally:
        flush_seen(force=True)

    return {
        "funnel": funnel,
        "candidates_by_track": candidates_by_track,
        "saved_by_track": saved_by_track,
        "embedded": embedded,
    }


def print_report(result: Dict[str, Any], dry_run: bool) -> None:
    funnel: Counter = result["funnel"]
    print("\n📊 FUNNEL (berapa lowongan gugur di tiap tahap):")
    for k in FUNNEL_ORDER:
        if funnel.get(k):
            print(f"   {k:<24} {funnel[k]}")
    if dry_run:
        print("\n🔎 Kandidat per bidang (lolos filter murah, siap di-embed):")
        for name, titles in result["candidates_by_track"].items():
            print(f"   [{name}] {len(titles)} lowongan, contoh:")
            for t in titles[:8]:
                print(f"      - {t}")
        print(
            "\n(DRY RUN: tidak ada embedding dipakai dan tidak ada yang ditulis ke DB.)"
        )
    else:
        print(
            f"\n🎉 Fase B selesai. Embedding dipakai: {result['embedded']}/{MAX_JOBS_TO_EMBED}. "
            f"Tersimpan per bidang: {dict(result['saved_by_track'])}"
        )


def main(argv: List[str]) -> None:
    dry_run = "--dry-run" in argv
    only = next((a.split("=", 1)[1] for a in argv if a.startswith("--tracks=")), "")
    wanted = {x.strip() for x in only.split(",") if x.strip()}
    tracks = {
        k: v
        for k, v in TRACKS.items()
        if v.get("enabled", True) and (not wanted or k in wanted)
    }
    if not tracks:
        print("❌ Tidak ada bidang aktif. Periksa tracks.py / argumen --tracks.")
        return

    print(
        f"🔍 Ingest v2 {'(DRY RUN) ' if dry_run else ''}| bidang aktif: {list(tracks)}"
    )

    track_vecs: Dict[str, List[float]] = {}
    seen: Set[str] = set()
    try:
        from db import load_seen_keys, delete_old_seen

        seen = load_seen_keys(SEEN_RETENTION_DAYS)
        print(
            f"   Memori: {len(seen)} sidik jari lowongan yang sudah pernah dievaluasi."
        )
        if not dry_run:
            delete_old_seen(SEEN_RETENTION_DAYS)
    except Exception as e:
        print(f"   ⚠️ Gagal memuat memori DB ({e}); lanjut tanpa dedup lintas-run.")

    if not dry_run:
        track_vecs = sync_track_embeddings(tracks)

    raw_jobs = fetch_all(tracks)
    if not raw_jobs:
        print("⚠️ Tidak ada lowongan yang bisa diambil dari sumber manapun.")
        return

    result = process_jobs(raw_jobs, tracks, track_vecs, seen, dry_run=dry_run)
    print_report(result, dry_run)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:
        print(f"❌ Error Fatal: {e}")
        raise
