import os
import json
import time
from datetime import date
from typing import List, Dict, Any
from google import genai
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_API_KEY = os.getenv("GEMINI_EMBEDDING_API_KEY")
REASONING_API_KEY = os.getenv("GEMINI_REASONING_API_KEY")

# Dinamisasi Nama Model via .env (Fallback ke default jika lupa diisi)
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2-preview")
REASONING_MODEL = os.getenv("GEMINI_REASONING_MODEL", "gemini-3.5-flash-lite")

if not EMBEDDING_API_KEY or not REASONING_API_KEY:
    raise ValueError(
        "Fatal: GEMINI_EMBEDDING_API_KEY dan GEMINI_REASONING_API_KEY harus diisi di .env!"
    )

embedding_client = genai.Client(api_key=EMBEDDING_API_KEY)
reasoning_client = genai.Client(api_key=REASONING_API_KEY)

# === Rate-Limit Budget (Free Tier Gemini) ===
# Default sesuai limit yang berlaku sekarang; override lewat .env kalau berubah.
EMBEDDING_RPM = int(os.getenv("EMBEDDING_RPM", "100"))
EMBEDDING_TPM = int(os.getenv("EMBEDDING_TPM", "30000"))
EMBEDDING_RPD = int(os.getenv("EMBEDDING_RPD", "1000"))

REASONING_RPM = int(os.getenv("REASONING_RPM", "15"))
REASONING_TPM = int(os.getenv("REASONING_TPM", "250000"))
REASONING_RPD = int(os.getenv("REASONING_RPD", "500"))

# Estimasi kasar token per call (job desc ~3000 char, prompt reasoning JD+konteks ~8000 char)
_EST_TOKENS_PER_EMBED_CALL = 800
_EST_TOKENS_PER_REASONING_CALL = 2200

# TPM sering jadi pembatas NYATA, bukan RPM -> ambil interval paling aman dari keduanya
EMBEDDING_SLEEP = max(
    60 / EMBEDDING_RPM, 60 / (EMBEDDING_TPM / _EST_TOKENS_PER_EMBED_CALL)
)
REASONING_SLEEP = max(
    60 / REASONING_RPM, 60 / (REASONING_TPM / _EST_TOKENS_PER_REASONING_CALL)
)


class RateBudgetExceeded(Exception):
    """Dilempar saat kuota harian (RPD) suatu model sudah habis untuk hari ini."""

    pass


# Counter di memori, disinkronkan dari Supabase sekali per proses (penting karena
# hunt ini bisa dipicu berkali-kali sehari lewat cronjob.org, bukan cuma sekali).
_usage_cache = {"date": None, "embedding_calls": 0, "reasoning_calls": 0}


def _load_today_usage():
    global _usage_cache
    # Kuota harian Gemini reset tengah malam waktu Pasifik, jadi counter memakai
    # tanggal Pasifik (db.usage_today), bukan tanggal server.
    try:
        from db import usage_today

        today_str = usage_today().isoformat()
    except Exception:
        today_str = date.today().isoformat()
    if _usage_cache["date"] == today_str:
        return
    try:
        from db import get_today_usage

        remote = get_today_usage()
        _usage_cache = {
            "date": today_str,
            "embedding_calls": remote.get("embedding_calls", 0),
            "reasoning_calls": remote.get("reasoning_calls", 0),
        }
    except Exception as e:
        print(
            f"   ⚠️ Gagal memuat usage counter dari DB (proteksi RPD lintas-run nonaktif): {e}"
        )
        _usage_cache = {"date": today_str, "embedding_calls": 0, "reasoning_calls": 0}


def _bump_usage(api_type: str):
    global _usage_cache
    _usage_cache[f"{api_type}_calls"] += 1
    try:
        from db import increment_usage

        increment_usage(api_type, _usage_cache[f"{api_type}_calls"])
    except Exception as e:
        print(f"   ⚠️ Gagal menyimpan usage counter ke DB: {e}")


def get_embedding(text: str, max_retries: int = 3) -> List[float]:
    if not text or not text.strip():
        raise ValueError("Teks untuk embedding tidak boleh kosong.")

    _load_today_usage()
    if _usage_cache["embedding_calls"] >= EMBEDDING_RPD:
        raise RateBudgetExceeded(
            f"Kuota harian Embedding ({EMBEDDING_RPD} RPD) sudah tercapai hari ini."
        )

    # Mekanisme Auto-Retry + Backoff untuk menghindari 429 Rate Limit
    for attempt in range(max_retries):
        try:
            response = embedding_client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text.strip(),
                config={"task_type": "SEMANTIC_SIMILARITY"},
            )
            _bump_usage("embedding")
            time.sleep(EMBEDDING_SLEEP)  # jaga throughput tetap di bawah RPM/TPM
            return response.embeddings[0].values[:768]
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 3  # Backoff: 3s, 6s
                print(
                    f"         ⚠️ Limit Gemini Embedding (Mencoba ulang dalam {sleep_time}s)..."
                )
                time.sleep(sleep_time)
            else:
                print(
                    f"         ❌ Error saat generate embedding setelah {max_retries} percobaan: {e}"
                )
                raise


def get_gemini_reasoning(
    system_prompt: str, user_prompt: str, max_retries: int = 3
) -> Dict[str, Any]:
    _load_today_usage()
    if _usage_cache["reasoning_calls"] >= REASONING_RPD:
        raise RateBudgetExceeded(
            f"Kuota harian Reasoning ({REASONING_RPD} RPD) sudah tercapai hari ini."
        )

    for attempt in range(max_retries):
        try:
            response = reasoning_client.models.generate_content(
                model=REASONING_MODEL,
                contents=user_prompt,
                config={
                    "system_instruction": system_prompt,
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            )
            result = json.loads(response.text)
            _bump_usage("reasoning")
            time.sleep(REASONING_SLEEP)  # jaga throughput tetap di bawah RPM
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 3
                print(
                    f"   ⚠️ Limit Gemini Reasoning (Mencoba ulang dalam {sleep_time}s)..."
                )
                time.sleep(sleep_time)
            else:
                print(
                    f"   ❌ Error saat request reasoning ke Gemini setelah {max_retries} percobaan: {e}"
                )
                raise


if __name__ == "__main__":
    print("🧠 Menguji AI Engine (Dynamic Models & Retry System)...")
    try:
        dummy_text = "Saya adalah AI Solutions Developer."
        emb = get_embedding(dummy_text)
        print(f"✅ Embedding Berhasil! Model: {EMBEDDING_MODEL} | Dimensi: {len(emb)}")

        sys_prompt = "Balas HANYA dengan format JSON: {'status': 'ok'}"
        result = get_gemini_reasoning(sys_prompt, "Test")
        print(f"✅ Reasoning Berhasil! Model: {REASONING_MODEL} | Hasil: {result}")
    except Exception as e:
        print(f"❌ Gagal: {e}")
