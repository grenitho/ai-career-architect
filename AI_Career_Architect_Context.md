# 🧠 PROJECT BIBLE: AI Career Architect & Reasoning Engine
**Status:** Blueprint Final & Context Anchor
**Update v3 (Okt 2026):** dokumen ini dipertahankan sebagai catatan desain awal. Beberapa hal sudah berubah: reasoning memakai **Gemini** (bukan Groq), schema database lengkap ada di **`migration_v2.sql`** (5 tabel, bukan 2), sumber lowongan & track diperluas, dan filter region/bahasa diperketat — rincian di **`UPGRADE_V3.md`** dan `README.md`.
**Tujuan Dokumen:** Dokumen ini adalah "Source of Truth" untuk proyek AI Career Architect. Baca dan pahami seluruh konteks di bawah ini sebelum memberikan jawaban, menulis kode, atau memberikan saran arsitektur.

---

## 1. VISI & FILOSOFI PROYEK
**AI Career Architect** adalah alat otomasi karir pasif yang memindai lowongan kerja remote global, menyaringnya, dan mencocokkannya dengan profil pengguna menggunakan Vector Search & LLM Reasoning. 

**ATURAN EMAS (CONSTRAINTS):**
1. **Kualitas > Kuantitas:** Hanya menargetkan 10-20 lowongan *highly-matched* per hari.
2. **Human-in-the-Loop (NO AUTO-APPLY):** Tool ini TIDAK BOLEH mengirim email lamaran atau apply otomatis. Tugas tool hanya: Filter -> Match -> Beri Alasan Logis -> Kirim Link agar user apply manual.
3. **Zero Heavy Storage:** Tool tidak menyimpan file PDF/Video mentah di database. PDF diekstrak jadi teks. Video di-host di YouTube (Unlisted) dan hanya ringkasan teksnya yang disimpan.
4. **100% Free Tier:** Seluruh infrastruktur harus berjalan di batas gratis (Free Tier) selamanya untuk skala 10-20 job/hari.

---

## 2. TECH STACK (100% FREE TIER)
*   **Compute & Scheduler:** GitHub Actions (Cron Job harian, 2000 menit/bulan).
*   **Database & Vector Store:** Supabase (PostgreSQL + `pgvector` extension).
*   **AI Embeddings:** Google Gemini API (`gemini-embedding-2-preview`).
*   **AI Reasoning & Analysis:** Gemini (`gemini-3.5-flash-lite`).
*   **PDF Parsing:** `pypdf` / `pdfplumber` (Dieksekusi lokal di runner GitHub Actions).
*   **Job Data Source:** JSearch via RapidAPI (Free tier 500 req/bulan) atau RemoteOK JSON API atau Source lain yang dirasa sesuai.
*   **Delivery/Notification:** Telegram Bot API (Push notification ke user).

---

## 3. DATABASE SCHEMA (SUPABASE)
Berikut adalah struktur tabel PostgreSQL yang wajib digunakan:

```sql
-- Aktifkan ekstensi vector
create extension if not exists vector;

-- Tabel untuk menyimpan Profil, CV, dan Dokumentasi Proyek User
create table user_knowledge (
  id serial primary key,
  type text, -- 'cv', 'project_doc', 'project_video_summary'
  title text, -- misal: 'CV - Fullstack', 'Proyek: AI CRM System'
  text_content text, -- Teks bersih hasil ekstrak PDF/Transkrip Video
  asset_url text, -- Link ke PDF asli (Google Drive) atau Video (YouTube)
  embedding vector(768), -- Dimensi embedding Gemini
  created_at timestamp default now()
);

-- Tabel untuk menyimpan Lowongan yang sudah diproses hari ini
create table daily_jobs (
  id serial primary key,
  job_title text,
  company text,
  description text,
  apply_url text,
  match_score int, -- 0-100
  ai_reasoning jsonb, -- Menyimpan JSON hasil reasoning Groq
  processed_date date default current_date,
  embedding vector(768)
);

---
## 4. PIPELINE & ARSITEKTUR SISTEM
Sistem berjalan dalam 3 fase utama via GitHub Actions Cron (misal: 07:00 WIB):

Fase A: Knowledge Base (Dijalankan manual/hanya saat ada proyek baru)
User menyediakan PDF/Link Video.
Script Python (knowledge_builder.py) mengekstrak teks dari PDF.
Teks di-embed menggunakan Gemini -> Disimpan ke tabel user_knowledge.

Fase B: Ingestion & Pre-Filtering (Harian)
Script (ingest.py) menarik 50-100 lowongan dari API.
Filter kasar: Buang yang tidak mengandung keyword inti user (misal: "Python", "Backend").
Sisakan 20-30 lowongan potensial -> Di-embed -> Simpan ke daily_jobs.

Fase C: Vector Matching & Deep Reasoning (Harian)
Vector Search: Query Supabase menggunakan pgvector untuk mencari jarak kosinus antara daily_jobs.embedding dan user_knowledge.embedding. Ambil Top 10.
Deep Reasoning (Groq): Untuk Top 10, kirim JD dan text_content portofolio yang match ke Groq.
Delivery: Format hasil JSON dari Groq menjadi pesan Telegram Markdown dan kirim ke user.

---
## 5. CORE LOGIC: PROMPT ENGINEERING (GROQ)
Ini adalah "otak" dari sistem. Prompt ini WAJIB digunakan untuk menghasilkan output yang terstruktur dan logis.
GROQ_REASONING_PROMPT = """
Kamu adalah Head of Engineering / Tech Recruiter tingkat global.
Tugasmu adalah menganalisis kecocokan antara Lowongan Pekerjaan dan Profil Kandidat.

[DESKRIPSI PEKERJAAN (JD)]:
{job_description}

[PROFIL & PROYEK KANDIDAT (Konteks Relevan)]:
{matched_user_knowledge_text}

TUGAS ANALISIS:
1. Berikan skor kecocokan (0-100) berdasarkan kesamaan skill, arsitektur, dan domain.
2. Buat 3 poin "MENGAPA COCOK" yang SANGAT SPESIFIK. Hubungkan requirement di JD secara eksplisit dengan fitur/arsitektur di proyek kandidat. JANGAN gunakan bahasa generik/klise.
3. Identifikasi 1 "Skill Gap" (kekurangan) kandidat untuk JD ini, dan berikan saran singkat cara menutupinya sebelum interview.
4. Berikan 2 "Talking Points" (Pertanyaan cerdas) yang bisa ditanyakan kandidat saat interview untuk mengesankan perekrut.

FORMAT OUTPUT (WAJIB JSON VALID):
{{
  "score": 85,
  "match_reasons": ["Alasan 1 yang spesifik", "Alasan 2", "Alasan 3"],
  "skill_gap": "Penjelasan skill gap dan cara belajar/mempersiapkannya",
  "interview_talking_points": ["Pertanyaan 1", "Pertanyaan 2"]
}}
"""

---

## 6. STRUKTUR FOLDER & DEPLOYMENT
Struktur Repo GitHub:

ai-career-architect/
├── .github/workflows/daily_hunt.yml  # Cron job GitHub Actions
├── main.py                           # Orkestrator utama (Fase B & C)
├── knowledge_builder.py              # Script untuk ingest CV/Proyek (Fase A)
├── ingest.py                         # Logika ambil data dari API
├── ai_engine.py                      # Logika Gemini Embedding & Groq Reasoning
├── db.py                             # Koneksi & Query Supabase (pgvector)
├── notifier.py                       # Logika format & kirim Telegram
├── requirements.txt                  # supabase, google-generativeai, pypdf, requests
└── README.md

GitHub Actions Secrets yang dibutuhkan:
SUPABASE_URL, SUPABASE_KEY
GEMINI_API_KEY, GROQ_API_KEY
RAPIDAPI_KEY (Untuk JSearch)
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID