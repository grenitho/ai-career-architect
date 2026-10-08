import os
import json
from dotenv import load_dotenv

from db import (
    find_relevant_knowledge,
    update_job_reasoning,
    get_unanalyzed_jobs,
    delete_old_jobs,
)
from ai_engine import get_gemini_reasoning, RateBudgetExceeded
from tracks import TRACKS, CANDIDATE_NOTES

load_dotenv()

# Batas jumlah job yang dianalisis dalam SATU run (pengaman di atas RPD harian).
MAX_JOBS_TO_REASON = int(os.getenv("MAX_JOBS_TO_REASON", "80"))
RETENTION_DAYS = int(os.getenv("JOBS_RETENTION_DAYS", "7"))
# Berhenti jika sekian job berturut-turut gagal (indikasi limit/outage Gemini).
MAX_CONSECUTIVE_FAILURES = 3

REASONING_PROMPT = """
Kamu adalah Tech & Operations Recruiter global yang adil terhadap kandidat non-tradisional.
Tugasmu menganalisis kecocokan antara Lowongan dan Profil Kandidat.

[BIDANG TARGET LOWONGAN INI]:
{track_label}

[DESKRIPSI PEKERJAAN (JD)]:
{job_description}

[PROFIL & PROYEK KANDIDAT (Konteks Relevan)]:
{matched_user_knowledge_text}

[CATATAN & KENDALA KANDIDAT]:
{candidate_notes}

TUGAS ANALISIS:
1. Berikan skor kecocokan (0-100). Jika profil TIDAK RELEVAN sama sekali dengan JD, skor di bawah 30.
2. Buat 3 poin "MENGAPA COCOK" atau "MENGAPA TIDAK COCOK" yang spesifik berdasarkan teks di atas.
3. Identifikasi 1 "Skill Gap" kandidat untuk JD ini.
4. Berikan 2 "Talking Points" (pertanyaan cerdas) untuk interview.
5. Tulis "cv_angle": 1 kalimat tentang cara memposisikan pengalaman kandidat (termasuk pengalaman usaha sendiri) agar relevan untuk JD ini.
6. Nilai "region_eligibility" untuk kandidat di Indonesia (UTC+7): "worldwide", "apac_ok", "restricted" (hanya negara/region tertentu atau wajib jam kerja zona lain yang tidak masuk akal), atau "unclear".
7. Tandai "suspicious": true jika JD mengindikasikan penipuan (minta bayar di muka, wawancara hanya via chat pribadi, gaji tidak masuk akal untuk tugasnya).
8. Verifikasi postingan ini benar-benar LOWONGAN KERJA dari pemberi kerja. Jika ini iklan freelancer menawarkan jasa ("for hire", "I am available", "you pay after I fix..."), iklan pencari kerja, atau bukan lowongan sama sekali, set "is_job": false.

FORMAT OUTPUT (WAJIB JSON VALID):
{{
  "score": 25,
  "match_reasons": ["Alasan 1 yang spesifik", "Alasan 2", "Alasan 3"],
  "skill_gap": "Penjelasan skill gap dan cara mempersiapkannya",
  "interview_talking_points": ["Pertanyaan 1", "Pertanyaan 2"],
  "cv_angle": "Satu kalimat cara memposisikan pengalaman kandidat",
  "region_eligibility": "worldwide",
  "is_job": true,
  "suspicious": false
}}
"""


def _truthy(v) -> bool:
    return v is True or str(v).strip().lower() == "true"


def clean_old_jobs():
    print("\n🧹 Pembersihan database harian...")
    try:
        delete_old_jobs(RETENTION_DAYS)
        print(f"   ✅ Lowongan lebih dari {RETENTION_DAYS} hari telah dihapus.")
    except Exception as e:
        print(f"   ❌ Gagal membersihkan database: {e}")


def run_daily_matching():
    print("🚀 Fase C (v2): Vector Matching & Deep Reasoning...")
    clean_old_jobs()

    print(
        "\n[1/4] Mengambil lowongan yang belum dianalisis (semua hari, similarity tertinggi dulu)..."
    )
    jobs_to_analyze = get_unanalyzed_jobs(limit=MAX_JOBS_TO_REASON)
    if not jobs_to_analyze:
        print("⚠️ Tidak ada lowongan yang perlu dianalisis.")
        return
    print(
        f"   ✅ {len(jobs_to_analyze)} lowongan akan dianalisis (batas per-run: {MAX_JOBS_TO_REASON})."
    )

    reasoned_count = 0
    consecutive_failures = 0

    for i, job in enumerate(jobs_to_analyze, 1):
        print(
            f"\n--- [{i}/{len(jobs_to_analyze)}] {job['job_title']} di {job['company']} ---"
        )

        raw_embedding = job["embedding"]
        try:
            job_embedding = (
                json.loads(raw_embedding)
                if isinstance(raw_embedding, str)
                else raw_embedding
            )
        except Exception as e:
            print(f"   ❌ Gagal parsing embedding: {e}")
            continue

        print("   [2/4] Vector search ke user_knowledge...")
        try:
            # Threshold permisif karena basis pengetahuan hanya beberapa dokumen;
            # penyaringan relevansi yang berarti sudah terjadi di ingest.py.
            matches = find_relevant_knowledge(
                job_embedding=job_embedding, match_threshold=0.1, match_count=2
            )
            context_text = (
                "\n\n---\n\n".join(m["text_content"] for m in matches)
                if matches
                else "Tidak ada data profil kandidat yang tersedia di database."
            )
        except Exception as e:
            print(f"   ❌ Gagal vector search: {e}")
            continue

        track_key = job.get("track")
        track_label = TRACKS.get(track_key, {}).get("label", track_key or "Umum")

        print("   [3/4] Deep reasoning (Gemini)...")
        try:
            prompt = REASONING_PROMPT.format(
                track_label=track_label,
                job_description=job["description"][:4000],
                matched_user_knowledge_text=context_text[:4000],
                candidate_notes=CANDIDATE_NOTES,
            )
            result = get_gemini_reasoning(
                "Anda adalah AI Recruiter ahli. Balas HANYA dengan JSON valid sesuai format yang diminta.",
                prompt,
            )
            score = max(0, min(100, int(result.get("score", 0))))

            # Pengaman deterministik: LLM kadang terlalu murah hati.
            # v3.3: postingan yang bukan lowongan kerja (iklan jasa/for-hire)
            # dipatok maksimal 10 — tidak akan pernah lolos ambang notifikasi.
            if result.get("is_job") is False:
                score = min(score, 10)
            elif (
                _truthy(result.get("suspicious"))
                or result.get("region_eligibility") == "restricted"
            ):
                score = min(score, 25)

            reasoned_count += 1
            consecutive_failures = 0
            print(f"   ✅ Skor: {score}/100")
        except RateBudgetExceeded as e:
            print(f"   🛑 {e} Menghentikan sisa analisis run ini.")
            break
        except Exception as e:
            consecutive_failures += 1
            print(f"   ❌ Gagal reasoning: {e}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(
                    f"   🛑 {MAX_CONSECUTIVE_FAILURES} kegagalan berturut-turut, berhenti (kemungkinan limit/outage)."
                )
                break
            continue

        print("   [4/4] Menyimpan hasil...")
        try:
            update_job_reasoning(
                job_id=job["id"], match_score=score, ai_reasoning=result
            )
        except Exception as e:
            print(f"   ❌ Gagal update database: {e}")

    print(
        f"\n🎉 Fase C selesai! {reasoned_count} lowongan dianalisis ({reasoned_count}/{MAX_JOBS_TO_REASON})."
    )


if __name__ == "__main__":
    run_daily_matching()
