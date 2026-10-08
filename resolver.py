"""Fase D.5 (v3.7): Apply Route Resolver.

Memverifikasi bahwa link apply dari lowongan yang akan dikirim ke Telegram benar-benar
bisa dipakai. Bila link utama 'bertembok' (account wall/paywall) atau mati, modul ini
mencarikan jalur alternatif secara otomatis:

  1. Situs perusahaan  — diekstrak dari teks deskripsi (format WWR: "URL: https://...")
  2. Halaman karir     — probe path umum (/careers, /jobs, /apply, ...) + deteksi ATS
                         (Lever, Greenhouse, Ashby, BambooHR, Workable, ...)
  3. Email kontak      — dari halaman /contact perusahaan (mailto:)
  4. Cross-posting     — lowongan yang sama di board lain, via JSearch (hemat kuota:
                         maksimal RESOLVE_MAX_JSEARCH panggilan per run)

Dipanggil hanya untuk top ~10 lowongan di tahap notifikasi, jadi biaya HTTP kecil.
Prinsip: hanya melaporkan yang TERVERIFIKASI — tidak pernah mengarang jalur.
Nonaktifkan lewat env RESOLVE_APPLY_LINKS=0.
"""
import os
import re
import urllib.parse
from typing import Any, Dict, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Konfigurasi (override lewat env / repo variables)
# ---------------------------------------------------------------------------

RESOLVE_ENABLED = os.getenv("RESOLVE_APPLY_LINKS", "1").strip().lower() not in ("0", "false", "no")
RESOLVE_MAX_JOBS = int(os.getenv("RESOLVE_MAX_JOBS", "10"))        # lowongan yang diverifikasi per run
RESOLVE_MAX_PROBES = int(os.getenv("RESOLVE_MAX_PROBES", "6"))     # budget probe situs perusahaan per run
RESOLVE_MAX_JSEARCH = int(os.getenv("RESOLVE_MAX_JSEARCH", "3"))   # budget call JSearch cross-post per run

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"

BROWSER_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

# Domain yang DIKETAHUI meminta akun/bayaran bagi pelamar (fast-path tanpa HTTP).
KNOWN_WALL_DOMAINS = (
    "weworkremotely.com", "flexjobs.com", "virtualvocations.com", "jobleads.com",
)

# Penanda halaman bertembok (dicari di HTML link apply).
WALL_MARKERS = (
    "create an account to view", "sign in to apply", "log in to apply",
    "sign up to apply", "register to apply", "to view full job details",
    "membership required", "subscribe to apply", "upgrade to apply",
    "create an account to apply",
)

CAREERS_PATHS = (
    "/careers", "/jobs", "/career", "/openings", "/work-with-us",
    "/join-us", "/about/careers", "/company/careers", "/apply",
)

ATS_HINTS = (
    "lever.co", "greenhouse.io", "ashbyhq.com", "bamboohr.com", "workable.com",
    "smartrecruiters.com", "breezy.hr", "jazz.co", "teamtailor.com", "personio.",
    "recruitee.com", "jobvite.com", "icims.com", "myworkdayjobs.com", "dover.io",
    "rippling.com", "zoho.com/recruit", "apply.workable.com", "boards.",
)

EMAIL_NOISE = (
    "sentry", "example.", "no-reply", "noreply", "unsubscribe", "privacy@",
    "legal@", "domainmarket", "wixpress", ".png", ".jpg", ".jpeg", ".svg",
    ".webp", ".gif", "@2x", "godaddy", "namecheap", "youremail", "email.com",
)

# Domain board/agregator — jangan dianggap "situs perusahaan".
BOARD_DOMAINS = (
    "weworkremotely.com", "remoteok.com", "remotive.com", "himalayas.app",
    "jobicy.com", "arbeitnow.com", "workingnomads.com", "n8n.io",
    "news.ycombinator.com", "linkedin.com", "indeed.com", "glassdoor.com",
    "ziprecruiter.com", "simplyhired.com", "rapidapi.com",
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def domain_of(url: Optional[str]) -> str:
    try:
        netloc = (urllib.parse.urlsplit(str(url or "")).netloc or "").lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def is_wall_domain(url: Optional[str]) -> bool:
    d = domain_of(url)
    return any(d == w or d.endswith("." + w) for w in KNOWN_WALL_DOMAINS)


def _get(url: str, timeout: int) -> Optional[requests.Response]:
    try:
        return requests.get(url, headers=BROWSER_UA, timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# 1. Klasifikasi link apply utama
# ---------------------------------------------------------------------------

def classify_apply_url(url: Optional[str], timeout: int = 8) -> Tuple[str, str]:
    """Return (status, bukti). status: 'ok' | 'wall' | 'dead' | 'unknown' | 'missing'."""
    if not url or not str(url).strip():
        return "missing", "tanpa URL"
    if is_wall_domain(url):
        return "wall", "domain dikenal bertembok"
    r = _get(str(url), timeout)
    if r is None:
        return "unknown", "timeout/koneksi"
    if r.status_code in (401, 403):
        return "wall", f"HTTP {r.status_code}"
    if r.status_code in (404, 410):
        return "dead", f"HTTP {r.status_code}"
    if r.status_code >= 500:
        return "unknown", f"HTTP {r.status_code}"
    low = (r.text or "")[:300000].lower()
    for m in WALL_MARKERS:
        if m in low:
            return "wall", f"'{m}'"
    return "ok", ""


# ---------------------------------------------------------------------------
# 2. Ekstraksi situs perusahaan dari deskripsi
# ---------------------------------------------------------------------------

_URL_PATTERNS = (
    r"URL:\s*(https?://[^\s,;)\"'<]+)",                                    # format WWR
    r"(?:website|web\s?site|company\s+site|homepage)\s*[:\-]\s*(https?://[^\s,;)\"'<]+)",
    r"(?:visit|see)\s+(?:us\s+)?(?:at|:)\s*(https?://[^\s,;)\"'<]+)",
)


def extract_company_site(description: Optional[str]) -> Optional[str]:
    text = description or ""
    for pat in _URL_PATTERNS:
        m = re.search(pat, text[:4000], re.IGNORECASE)
        if m:
            url = m.group(1).rstrip(".,;")
            d = domain_of(url)
            if d and not any(b in d for b in BOARD_DOMAINS):
                return url
    return None


# ---------------------------------------------------------------------------
# 3. Probe halaman karir perusahaan
# ---------------------------------------------------------------------------

def probe_careers(site: Optional[str], timeout: int = 6, max_probes: int = 5) -> Optional[str]:
    """Coba path karir umum di situs perusahaan. Return URL ATS langsung bila ada,
    URL halaman karir bila terdeteksi, selain itu None."""
    base = (site or "").rstrip("/")
    if not base:
        return None
    tried = 0
    for path in CAREERS_PATHS:
        if tried >= max_probes:
            break
        tried += 1
        r = _get(base + path, timeout)
        if r is None or r.status_code != 200:
            continue
        low = (r.text or "").lower()
        # Prioritas: link ATS eksplisit (langsung ke daftar lowongan perusahaan).
        for hint in ATS_HINTS:
            if hint in low:
                for mm in re.finditer(r'href="(https?://[^"]+)"', r.text or "", re.I):
                    if hint in mm.group(1).lower():
                        return mm.group(1)
                return str(r.url)
        # Halaman karir organik: ada kata apply/opening/position + konteks karir.
        if re.search(r"\b(apply|opening|position|hiring)\b", low) and re.search(
            r"\b(career|jobs?|hiring|opening|position|team)\b", low
        ):
            return str(r.url)
    return None


# ---------------------------------------------------------------------------
# 4. Email kontak perusahaan
# ---------------------------------------------------------------------------

def extract_contact_email(site: Optional[str], timeout: int = 6) -> Optional[str]:
    base = (site or "").rstrip("/")
    if not base:
        return None
    for path in ("/contact", "/contact-us", "/about", ""):
        r = _get(base + path, timeout)
        if r is None or r.status_code != 200:
            continue
        body = r.text or ""
        emails = re.findall(r"mailto:([^\"'>?\s]+)", body)
        emails += re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", body)
        for e in emails:
            e = e.strip().lower().rstrip(".,;")
            if any(n in e for n in EMAIL_NOISE) or len(e) > 60:
                continue
            return e
    return None


# ---------------------------------------------------------------------------
# 5. Cross-posting via JSearch (1 call kuota per percobaan)
# ---------------------------------------------------------------------------

def find_crosspost(title: str, company: str, exclude_domain: str = "", timeout: int = 12) -> Optional[str]:
    if not RAPIDAPI_KEY or not title:
        return None
    q = (f'"{title[:60]}" {company}'.strip())[:100]
    try:
        r = requests.get(
            f"https://{RAPIDAPI_HOST}/search-v2",
            headers={"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST},
            params={"query": q, "page": "1", "num_pages": "1"},
            timeout=timeout,
        )
        data = r.json()
    except Exception:
        return None
    raw = data.get("data") if isinstance(data, dict) else None
    items = raw.get("jobs", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    for j in items or []:
        url = (j.get("job_apply_link") or "").strip()
        d = domain_of(url)
        if (
            url
            and d
            and d != exclude_domain
            and not is_wall_domain(url)
            and "weworkremotely" not in d
        ):
            return url
    return None


# ---------------------------------------------------------------------------
# Orkestrasi per-lowongan
# ---------------------------------------------------------------------------

def resolve_job(job: Dict[str, Any], budget: Dict[str, int]) -> Dict[str, Any]:
    """Verifikasi jalur apply satu lowongan. `budget` dipakai bersama antar-lowongan
    dalam satu run: {'probes': int, 'jsearch': int} — dimutasi di tempat."""
    out: Dict[str, Any] = {
        "status": None, "evidence": "", "company_site": None,
        "careers": None, "email": None, "crosspost": None,
    }
    url = (job.get("apply_url") or "").strip()
    dom = domain_of(url)

    out["status"], out["evidence"] = classify_apply_url(url)
    out["company_site"] = extract_company_site(job.get("description") or "")

    if out["status"] in ("wall", "dead", "missing"):
        if out["company_site"] and budget.get("probes", 0) > 0:
            budget["probes"] = budget.get("probes", 0) - 1
            try:
                out["careers"] = probe_careers(out["company_site"])
                out["email"] = extract_contact_email(out["company_site"])
            except Exception:
                pass
        if budget.get("jsearch", 0) > 0:
            budget["jsearch"] = budget.get("jsearch", 0) - 1
            try:
                out["crosspost"] = find_crosspost(
                    job.get("job_title", ""), job.get("company", ""), dom
                )
            except Exception:
                pass
    return out


if __name__ == "__main__":
    # Uji mandiri cepat: python resolver.py
    demo = {
        "job_title": "Software Developer AI Coding",
        "company": "STEUART NUTRITION",
        "apply_url": "https://weworkremotely.com/remote-jobs/steuart-nutrition-software-developer-ai-coding",
        "description": (
            "Headquarters: Minnesota URL: https://www.steuartnutrition.com/ "
            "Steuart Nutrition is a GMP-certified contract manufacturer. "
            "We run on Extreme Ownership, clear communication and fast turnaround."
        ),
    }
    result = resolve_job(demo, {"probes": RESOLVE_MAX_PROBES, "jsearch": 0})
    print("Hasil resolve (tanpa JSearch, sandbox):")
    for k, v in result.items():
        print(f"  {k:<12}: {v}")
