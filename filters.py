"""Logika murni (tanpa dependensi eksternal) untuk menyaring & merutekan lowongan.

Sengaja dipisah dari ingest.py supaya bisa dites offline tanpa Supabase/Gemini:
    python test_filters.py

V3 (Okt 2026):
  - Daftar negara diperluas (v2 hanya US/UK/CA/EU/DE/AU — kasus "Jutland Denmark"
    dan sejenisnya lolos).
  - location_verdict() kini juga memeriksa NEGARA DI JUDUL ("US Marketing Lead"),
    kecuali deskripsinya memuat kata worldwide/anywhere/dsb.
  - Filter BARU requires_other_language(): membuang lowongan yang mensyaratkan
    bahasa non-Inggris/Indonesia ("Japanese & Korean Speaking", "fluent in German"),
    dengan pengecualian bila bahasanya hanya "nilai plus".
"""
import re
import html
import urllib.parse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# URL & kunci dedup
# ---------------------------------------------------------------------------

# Hanya parameter TRACKING yang dibuang. Parameter lain (mis. ?id=123, ?gh_jid=456)
# dipertahankan karena bisa jadi pembeda antar lowongan. (Versi lama membuang SEMUA
# query string, sehingga dua job berbeda di situs yang sama bisa dianggap satu.)
_TRACKING_PARAMS = {
    "ref", "referrer", "ref_src", "source", "src", "fbclid", "gclid", "trk",
    "trackingid", "refid", "mc_cid", "mc_eid", "lever-source", "lever-origin",
    "gh_src",
}


def normalize_url(url: Optional[str]) -> str:
    if not url:
        return ""
    try:
        p = urllib.parse.urlsplit(str(url).strip())
        query = [
            (k, v)
            for k, v in urllib.parse.parse_qsl(p.query)
            if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
        ]
        query.sort()
        return urllib.parse.urlunsplit(
            (
                p.scheme.lower(),
                p.netloc.lower(),
                p.path.rstrip("/"),
                urllib.parse.urlencode(query),
                "",
            )
        )
    except Exception:
        return str(url)


def title_company_key(title: str, company: str) -> str:
    # Format sama persis dengan memori lama di ingest.py (kompatibel dgn data lama).
    return f"{title}_{company}".lower().strip()


def job_keys(job: Dict[str, Any]) -> List[str]:
    """Semua 'sidik jari' sebuah lowongan: URL ternormalisasi + judul_perusahaan."""
    keys = []
    url_key = normalize_url(job.get("url"))
    if url_key:
        keys.append(url_key)
    keys.append(title_company_key(job.get("title", ""), job.get("company", "")))
    return keys


def clean_html(raw: Any) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(raw))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Umur lowongan
# ---------------------------------------------------------------------------


def parse_posted_at(posted_at: Any) -> Optional[datetime]:
    if not posted_at:
        return None
    try:
        if isinstance(posted_at, (int, float)):
            ts = posted_at / 1000 if posted_at > 1e11 else posted_at  # detik atau milidetik
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        s = str(posted_at).strip()
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            dt = parsedate_to_datetime(s)  # format RSS: "Tue, 29 Sep 2026 12:00:00 +0000"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def is_recent_enough(posted_at: Any, max_age_days: int) -> bool:
    """True kalau umur <= max_age_days, ATAU tanggal tidak diketahui (default aman)."""
    dt = parse_posted_at(posted_at)
    if dt is None:
        return True
    return (datetime.now(timezone.utc) - dt).days <= max_age_days


# ---------------------------------------------------------------------------
# Region: worldwide vs dibatasi negara tertentu
# ---------------------------------------------------------------------------

# Nama negara panjang (tanpa singkatan) — dipakai case-insensitive.
# INDONESIA sengaja TIDAK dimasukkan: kandidat tinggal di Indonesia, jadi lowongan
# "based in Indonesia" justru valid untuknya.
_COUNTRY_NAMES_LONG = (
    r"United\s+States|United\s+Kingdom|Britain|England|"
    r"Canada|Germany|France|Netherlands|Holland|Spain|Italy|Portugal|Switzerland|"
    r"Austria|Belgium|Ireland|Sweden|Norway|Denmark|Finland|Poland|Czechia|"
    r"Czech\s+Republic|Hungary|Romania|Bulgaria|Croatia|Slovenia|Slovakia|"
    r"Estonia|Latvia|Lithuania|Greece|Ukraine|European\s+Union|Europe|"
    r"Australia|New\s+Zealand|Japan|South\s+Korea|Korea|China|Singapore|India|"
    r"Pakistan|Philippines|Vietnam|Thailand|Brazil|Mexico|Argentina|Colombia|"
    r"Chile|Peru|South\s+Africa|Nigeria|Kenya|Egypt|UAE|Dubai|Saudi\s+Arabia|"
    r"Israel|Turkey"
)
_COUNTRIES = rf"(?:the\s+)?(?:US|USA|U\.S\.|UK|U\.K\.|EU|{_COUNTRY_NAMES_LONG})"

# Catatan: "no visa sponsorship" sengaja DIHAPUS dari versi lama. Frasa itu sangat
# umum di lowongan kontraktor remote yang tetap menerima kandidat internasional,
# jadi lebih banyak membuang lowongan bagus daripada menyaring yang salah.
_REGION_BLOCKLIST_RE = re.compile(
    rf"\b{_COUNTRIES}\s+(?:citizens?|residents?|nationals?)\s+only\b"
    rf"|\bmust\s+(?:be\s+)?(?:based|located|residing|living|reside|live)\s+(?:in|within)\s+{_COUNTRIES}\b"
    rf"|\b(?:currently\s+)?(?:based|located|resident|living)\s+in\s+{_COUNTRIES}\b"
    rf"|\bresidents?\s+of\s+{_COUNTRIES}\b"
    rf"|\bwithin\s+{_COUNTRIES}\s+only\b"
    rf"|\bauthori[sz](?:ed|ation)\s+to\s+work\s+in\s+{_COUNTRIES}\b"
    rf"|\beligible\s+to\s+work\s+in\s+{_COUNTRIES}\b"
    rf"|\bright\s+to\s+work\s+in\s+{_COUNTRIES}\b"
    rf"|\b(?:only|exclusively)\s+(?:considering|accepting|hiring|open\s+to)\s+(?:applicants|candidates|people|residents)?"
    rf"\s*(?:from|in|based\s+in|located\s+in)?\s*{_COUNTRIES}\b"
    rf"|\b(?:{_COUNTRY_NAMES_LONG})-based\b"
    rf"|\bUS-based\s+(?:candidates|applicants)?\b",
    re.IGNORECASE,
)

# Scan JUDUL: singkatan HANYA cocok huruf kapital (US/UK/EU) supaya kata "us"
# (mis. "Join us!") tidak kena; nama negara panjang case-insensitive via (?i:...).
_TITLE_COUNTRY_RE = re.compile(
    r"\b(?:US|USA|U\.S\.|UK|U\.K\.|EU)\b"
    rf"|\b(?i:{_COUNTRY_NAMES_LONG})\b"
)

# Kata yang menandakan lokasi terbuka untuk kandidat di Indonesia.
_OPEN_LOCATION_TOKENS = (
    "worldwide", "anywhere", "global", "any location", "international",
    "everywhere", "apac", "asia", "indonesia", "no restriction", "all countries",
)
_REMOTE_NOISE_RE = re.compile(
    r"\b(?:fully\s+remote|100%\s*remote|remote|work\s+from\s+home|wfh)\b", re.IGNORECASE
)


def _flatten_location(location: Any) -> str:
    if not location:
        return ""
    if isinstance(location, (list, tuple, set)):
        return ", ".join(str(x) for x in location if x).lower()
    return str(location).lower()


def location_verdict(location: Any, text: str, title: Optional[str] = None) -> Tuple[str, str]:
    """Kembalikan (verdict, catatan). verdict: 'ok' | 'unknown' | 'restricted'.

    Urutan: (1) field lokasi terstruktur dari API sumber (paling andal), lalu
    (2) regex pada teks deskripsi, lalu (3) V3: nama negara di JUDUL — kecuali
    deskripsi memuat token terbuka (worldwide/anywhere/...) sehingga dibiarkan
    'unknown' untuk dinilai tahap reasoning.
    """
    loc = _flatten_location(location)
    loc_open = False
    if loc:
        stripped = re.sub(r"[\W_]+", " ", _REMOTE_NOISE_RE.sub("", loc)).strip()
        if stripped:  # ada informasi lokasi yang nyata (bukan sekadar "Remote")
            if any(tok in stripped for tok in _OPEN_LOCATION_TOKENS):
                loc_open = True
            else:
                return "restricted", f"lokasi: {loc[:60]}"

    m = _REGION_BLOCKLIST_RE.search(text or "")
    if m:
        return "restricted", f"teks: {m.group(0)[:60]}"

    # V3: negara di judul (mis. "US Marketing Lead", "... Jutland Denmark").
    if title:
        tm = _TITLE_COUNTRY_RE.search(title)
        if tm:
            text_l = (text or "").lower()
            if any(tok in text_l for tok in _OPEN_LOCATION_TOKENS):
                pass  # ada sinyal worldwide -> biarkan reasoning yang memutuskan
            else:
                return "restricted", f"judul: {tm.group(0)[:40]}"

    if loc_open:
        return "ok", f"lokasi: {loc[:60]}"
    return "unknown", ""


# ---------------------------------------------------------------------------
# Syarat bahasa non-Inggris (V3)
# ---------------------------------------------------------------------------

_LANGS = (
    r"japanese|korean|mandarin|cantonese|chinese|german|french|spanish|portuguese|"
    r"dutch|italian|russian|arabic|turkish|polish|swedish|norwegian|danish|finnish|"
    r"czech|romanian|hungarian|greek|hebrew|thai|vietnamese|filipino|tagalog|hindi|"
    r"urdu|bengali|persian|farsi|ukrainian|bulgarian|croatian|serbian|slovak|"
    r"lithuanian|latvian|estonian|slovenian|icelandic"
)
# Kata yang melembutkan: bahasa hanya "nilai plus", bukan syarat -> jangan dibuang.
_SOFTENER_RE = re.compile(
    r"\b(?:a\s+plus|plus|preferred|preferable|nice\s+to\s+have|bonus|advantage|"
    r"asset|would\s+be\s+beneficial|optional|not\s+required)\b",
    re.IGNORECASE,
)
_LANG_PATTERNS = (
    # "fluent in X", "must speak X", "bilingual X", "native X speaker", ...
    re.compile(rf"\b(?:fluent|fluency|native|bilingual|proficien\w*|speak|speaking|speaker|written\s+and\s+spoken|must\s+know)\b[^.!?]{{0,50}}\b(?:{_LANGS})\b", re.IGNORECASE),
    # "Japanese & Korean Speaking", "X language skills", "X speaker", ...
    re.compile(rf"\b(?:{_LANGS})\b[^.!?]{{0,40}}\b(?:speaker|speaking|language|fluency|fluent|native|proficiency)\b", re.IGNORECASE),
)


def requires_other_language(text: Any) -> Optional[str]:
    """Return cuplikan alasan bila lowongan MENSYARATKAN bahasa selain Inggris/Indonesia."""
    t = str(text or "")
    for pat in _LANG_PATTERNS:
        for m in pat.finditer(t):
            ctx = t[max(0, m.start() - 50): m.end() + 50]
            if _SOFTENER_RE.search(ctx):
                continue  # hanya "nilai plus" -> bukan syarat
            return m.group(0)[:60]
    return None


# ---------------------------------------------------------------------------
# Detektor "bukan lowongan": iklan jasa freelancer & pencari kerja (v3.3)
# Kasus nyata: RSS komunitas n8n bercampur posting [FOR HIRE] / "Same-day n8n
# workflow rescue $50" / "Looking for Remote Work" — iklan jasa, BUKAN lowongan.
# ---------------------------------------------------------------------------

_SERVICE_TITLE_RE = re.compile(
    r"\[\s*for\s+hire\s*\]?"
    r"|\bfor\s+hire\b"
    r"|\[\s*(?:offering|available|resume|job[ -]?seeker|services?)\s*\]"
    r"|\blooking\s+for\s+(?:remote\s+)?work\b"
    r"|\bavailable\s+for\b",
    re.IGNORECASE,
)
_SERVICE_TEXT_RE = re.compile(
    # "I am available ..." KECUALI konteks recruiter ("available for questions/chat")
    r"\bi\s+am\s+available\b(?!\s+(?:for|to)\s+(?:any\s+)?(?:questions?|clarifications?|chat|calls?|discussions?|info|interviews?))"
    r"|\bi'?m\s+available\s+(?:today|for\s+(?:hire|work|projects?|freelance))\b"
    r"|\bi\s+(?:offer|provide)\s+(?:my\s+)?(?:services|support)\b"
    r"|\bmy\s+services\b"
    r"|\blooking\s+for\s+(?:work|clients|gigs|new\s+projects)\b"
    r"|\byou\s+pay\s+(?:only\s+)?after\s+i\b"
    r"|\bi\s+will\s+(?:fix|build|deliver|reproduce|troubleshoot|debug)\b"
    r"|\bopen\s+to\s+(?:freelance|contract)\s+(?:work|projects|gigs)\b"
    r"|\b(?:dm|message)\s+me\s+with\s+(?:the|your)\s+(?:failing|problem|bug|workflow)\b",
    re.IGNORECASE,
)


def is_service_offer(title: str, text: str) -> bool:
    """True bila posting lebih mirip iklan jasa freelancer / pencari kerja
    daripada lowongan kerja dari pemberi kerja."""
    if _SERVICE_TITLE_RE.search(title or ""):
        return True
    return bool(_SERVICE_TEXT_RE.search((text or "")[:2500]))


# ---------------------------------------------------------------------------
# Indikasi scam
# ---------------------------------------------------------------------------

_SCAM_RE = re.compile(
    r"\b(?:registration|training|application|onboarding|processing|starter[- ]kit|security)\s+(?:fee|deposit)\b"
    r"|\b(?:pay|send|wire|transfer)\s+(?:us\s+|a\s+|an\s+)?(?:small\s+)?(?:fee|deposit|money|payment)\b"
    r"|\bpurchase\s+(?:your\s+own\s+)?(?:equipment|laptop|software)\s+(?:from|through)\s+(?:our|a)\s+(?:vendor|supplier)\b"
    r"|\b(?:interview|chat|hiring)\s+(?:is\s+)?(?:conducted\s+)?(?:only\s+)?(?:via|on|through|over)\s+(?:telegram|whatsapp|signal)\b"
    r"|\b(?:telegram|whatsapp)\s+(?:only|interview)\b"
    r"|\bcheck\s+(?:deposit|cashing)\b",
    re.IGNORECASE,
)


def is_scam_risk(text: str) -> bool:
    return bool(_SCAM_RE.search(text or ""))


# ---------------------------------------------------------------------------
# Filter judul & routing ke bidang (track)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=2048)
def _term_re(term: str) -> "re.Pattern[str]":
    # Lookaround (bukan \b) supaya istilah dengan simbol seperti "no-code",
    # "make.com", "c++" tetap cocok dengan benar.
    return re.compile(rf"(?<!\w){re.escape(term.lower())}(?!\w)")


def contains_term(text_lower: str, term: str) -> bool:
    return bool(_term_re(term).search(text_lower))


def is_title_excluded(title: str, exclude_terms: List[str]) -> bool:
    t = (title or "").lower()
    return any(contains_term(t, x) for x in exclude_terms)


def route_tracks(
    title: str, text: str, tracks: Dict[str, Dict[str, Any]]
) -> List[Tuple[str, bool, int]]:
    """Tentukan lowongan ini 'layak dicek' untuk bidang (track) mana saja.

    Layak jika: (judul mengandung istilah bidang DAN >= min_hits_with_title skill
    muncul di teks) ATAU (>= min_hits skill muncul di teks tanpa kecocokan judul).
    Return list (nama_track, title_hit, jumlah_skill_hit), terkuat di depan.
    """
    title_l = (title or "").lower()
    text_l = (text or "").lower()
    out: List[Tuple[str, bool, int]] = []
    for name, t in tracks.items():
        if not t.get("enabled", True):
            continue
        title_hit = any(contains_term(title_l, x) for x in t.get("title_terms", []))
        hits = sum(1 for x in t.get("skill_terms", []) if contains_term(text_l, x))
        if (title_hit and hits >= t.get("min_hits_with_title", 1)) or hits >= t.get(
            "min_hits", 3
        ):
            out.append((name, title_hit, hits))
    out.sort(key=lambda r: (r[1], r[2]), reverse=True)
    return out


def cosine_similarity(a: List[float], b: List[float]) -> float:
    import math

    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    ma = math.sqrt(sum(x * x for x in a))
    mb = math.sqrt(sum(y * y for y in b))
    if ma == 0 or mb == 0:
        return 0.0
    return dot / (ma * mb)
