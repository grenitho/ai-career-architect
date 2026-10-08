# 🚀 UPGRADE v3 — AI Career Architect
*(penjelasan bahasa manusia, bukan bahasa programmer)*

## Analogi sederhananya

Tool-mu itu seperti **pendulang emas 3 tahap**:
1. **Saringan kasar** (filter murah) — membuang kerikil: lowongan tua, scam, negara terbatas, bidang yang tidak cocok.
2. **Saringan halus** (embedding + similarity) — membandingkan tiap lowongan dengan "profil ideal" tiap bidang.
3. **Juri AI** (Gemini reasoning) — memberi skor 0–100; yang ≥ ambang batas dikirim ke Telegram.

**Masalah di v2:** saringan kasar lubang-lubangnya terlalu kecil dan kolamnya kurang luas.
Dari 346 lowongan unik, cuma **5** yang sampai ke saringan halus. Dan 5 itu kebetulan
sampah (kerjaan yang butuh bahasa Jepang/Korea, khusus Denmark, khusus US). Juri AI
menilai mereka 15–45 → di bawah ambang 60 → **Telegram-mu sunyi**. Tool-nya tidak rusak —
dia kelaparan bahan bagus.

## Yang diubah di v3 (7 hal)

**1. Kolamnya diperluas — 4 sumber baru (semua gratis, tanpa API key):**
- **HN "Who's Hiring"** — thread bulanan Hacker News; perusahaan tech sungguhan posting
  langsung. Run uji: **130 lowongan remote** dari thread Oktober 2026.
- **Working Nomads** — 56 lowongan remote terkumpul.
- **n8n Community Jobs** — papan kerja komunitas n8n: proyek freelance/kontrak automation
  dari seluruh dunia. Ini kolam paling pas untuk track AI Automation-mu.
- **Remotive full feed** — semua lowongan terbaru mereka, bukan cuma hasil kata kunci.

**2. Tiga bidang (track) baru — sesuai targetmu "management boleh, tidak harus IT":**
- 📋 **Operations & Project Management** — run uji langsung dapat **68 kandidat/hari**
- 💰 **Finance & Accounting** — modal 4 tahun Finance Manager-mu
- 🤝 **Customer Success** — jalur masuk paling ramah untuk profil non-tradisional

**3. Saringan sampah diperketat (biar juri AI tidak buang waktu):**
- Daftar negara diperluas dari 6 → 50+ (kasus "Jutland Denmark" tidak lolos lagi)
- Nama negara **di judul** ikut diperiksa ("US Marketing Lead" → ditolak)
- Filter BARU: lowongan yang **mensyaratkan bahasa asing** (Jepang, Korea, Jerman, dst.)
  langsung dibuang — kecuali bahasanya cuma "nilai plus"
- Bug laten diperbaiki: regex lama bisa salah menuduh teks apa pun yang menyebut nama
  negara ("we love Japanese culture" dulu bisa bikin lowongan ditolak)

**4. Saringan halus dilonggarkan ke titik yang sehat:** threshold similarity 0.58 → 0.52.
Filosofinya: biar **juri AI** yang jadi gerbang kualitas (dia sudah terbukti bekerja benar —
kasih skor 15–45 ke sampah), bukan saringan buta yang tidak mengerti konteks.

**5. Ambang notifikasi 60 → 50, kuota harian 10 → 15 lowongan.** Peluang lebih banyak,
prospek tetap terjaga (skor 50+ dari juri yang ketat itu sudah berarti "layak dilamar").

**6. Tidak ada lagi "sunyi misterius":** kalau tidak ada yang mencapai ambang, Telegram
tetap dikirimi pesan status: *"Terdekat: [judul] skor 47 — bila berhari-hari begini,
turunkan MIN_NOTIFY_SCORE."* Jadi kamu selalu tahu tool-nya hidup dan kenapa hasilnya kosong.

**7. Kebersihan & keamanan:**
- `test_api.py` **dihapus** (berisi RapidAPI key-mu yang hardcoded — **rotasi key itu sekarang**
  di dashboard RapidAPI!)
- `migration_v2.sql` **ditambahkan** — cetak biru lengkap 5 tabel database + fungsi
  vector-search, direkonstruksi dari kode. (Database lamamu TIDAK perlu diapa-apakan;
  ini untuk recovery/dokumentasi.)
- Catatan kandidat untuk juri AI (`CANDIDATE_NOTES`) dikoreksi sesuai ceritamu yang benar:
  Logaritma = karyawan (Finance Manager), sisanya usaha sendiri. Ditambah penegas:
  **100% remote harga mati**, kontrak/per-proyek diterima, bahasa Inggris fungsional-async.
- JSearch (RapidAPI) kini dipakai pintar: 2 query **rotasi harian** + kata "remote",
  ±60 call/bulan dari kuota 500 — bukan cuma fallback.

## Bukti uji (bukan teori)

| | v2 (log aslimu) | v3 (dry-run live, 6 Okt 2026) |
|---|---|---|
| Lowongan mentah | 649 | **1.105** |
| Unik setelah dedup | 346 | 459 |
| **Lolos ke tahap embedding** | **5** | **125** |
| Sampah terbuang (region/bahasa) | 34 / – | **94 / 8** |
| Kandidat per bidang | tak terpeta | ops_pm 68, cs_success 56, ai_automation 51, crm_ops 31, finance_ops 6, ... |

Filter juga diuji 12 kasus (6 harus lolos, 6 harus dibuang) — semua benar, termasuk
5 lowongan asli dari log-mu.

## Yang TIDAK berubah (kabar baik)

- cronjob.org jam 08:00 WIB-mu **tetap** — tidak perlu disentuh
- Tidak ada **secret/env baru** — semua sumber baru tanpa API key
- Database Supabase **tidak perlu migrasi** — schema sama
- Prinsip human-in-the-loop: tetap **tidak ada auto-apply**

## Ekspektasi setelah dipasang

Run pertama: ±125 lowongan di-embed, ±40–80 masuk penilaian juri (kuota 80/run),
kira-kira **5–15 notifikasi Telegram** (skor ≥50). Hari-hari berikutnya stabil
3–10/hari (dedup memori 45 hari mencegah pengulangan). Kuota gratis Gemini aman:
embedding ±125/1000 per hari, reasoning ±80/500 per hari.

## Cara pasang (pilih satu)

**Jalur A — paling gampang (rekomendasi):**
1. Bikin token fine-grained baru seperti kemarin, tapi **Contents: Read and Write**
   (hanya repo `ai-career-architect`, expiry pendek)
2. Kirim ke chat → saya push branch `upgrade-v3` ke repo-mu
3. Di GitHub muncul tombol **"Compare & pull request"** → kamu baca diff-nya → klik **Merge**
4. Revoke tokennya

**Jalur B — manual tanpa token write:**
File lengkap ada di folder `review/upgrade-v3-files/` (6 file + 1 patch). Buka tiap file
di GitHub web editor (repo → klik file → ikon pensil), timpa isinya dengan versi baru,
commit. `test_api.py` dihapus manual. `migration_v2.sql` dibuat sebagai file baru.

## Setelah terpasang — 2 PR kecil untukmu

1. **Rotasi RapidAPI key** (dashboard.rapidapi.com → key yang bocor di-delete, bikin baru,
   update di GitHub Secrets).
2. **Isi ulang knowledge base dengan resume final**: export resume baru ke PDF (Google Docs →
   Download as PDF), lalu jalankan `python knowledge_builder.py resume_baru.pdf profile "Orie Grenitho - Profile"`.
   Ini penting: juri AI menilai berdasarkan isi knowledge base. Resume lama/CV tes =
   penilaian tidak akurat. Idealnya tambah juga dokumen proyek ALIEN & Orion sebagai
   `project_doc`.

---

## Update v3.2 (7 Okt 2026) — perbaikan sumber

- **RemoteJobs.org DIBUANG**: konsisten HTTP 429 dari IP GitHub Actions (2 hari observasi:
  nol lowongan, hanya membuang waktu retry ±33 panggilan per run).
- **Pengganti: 5 feed kategori We Work Remotely** (RSS statis, terbukti stabil saat diprobe):
  Management & Finance (20 lowongan — untuk track ops_pm/finance_ops), Sales & Marketing (89 —
  cs_success/crm_ops/content_ops), Programming (25) & Full-Stack Programming (50 —
  ai_automation), Product (20 — ops_pm).
- Pesan usang di `knowledge_builder.py` diluruskan (sejak v3, acuan similarity filter ada di
  `tracks.py`, bukan dokumen profile).
- Kandidat pengganti yang DIUJI dan DITOLAK: TheMuse (403), Jobspresso (403), remote.co
  (timeout), paginasi Remotive (parameter diabaikan server), Himalayas limit>30 (tidak
  berpengaruh). RemoteJobs.org sendiri masih hidup dari IP rumahan — hanya IP GitHub
  Actions yang diblokir, jadi memang tidak berguna untuk pipeline ini.

---

## Update v3.3 (8 Okt 2026) — filter "bukan lowongan"

Kasus nyata: notifikasi Telegram berisi "Same-day n8n workflow rescue - $50 fixed"
dengan skor 85 — padahal itu **iklan freelancer menawarkan jasa**, bukan lowongan.
Papan Jobs komunitas n8n memang campur aduk: dari 25 posting terbaru, mayoritas
berprefiks [FOR HIRE]. Tag kategori RSS-nya tidak membantu (semuanya "Jobs").

Tiga lapis pertahanan baru:
1. **Regex judul** (`filters.is_service_offer`): [FOR HIRE], [OFFERING], "looking for
   (remote) work", "available for ...", dsb.
2. **Regex isi** (pola jual-jasa orang pertama): "I am available" (dengan pengecualian
   konteks recruiter: "I am available for questions/chat"), "you pay only after I",
   "I will fix/build/deliver", "my services", "hire me", "looking for clients/gigs",
   "open to freelance work", "DM me with the failing...".
3. **Juri AI** (main.py): tugas analisis #8 — verifikasi postingan benar-benar lowongan;
   field baru `"is_job"` di JSON; `is_job: false` → skor dipatok maksimal 10.

Counter funnel baru: `bukan_lowongan`. Berlaku untuk SEMUA sumber (bukan cuma n8n) —
thread HN atau feed lain yang kebobolan posting pencari kerja ikut tersaring.

---

## Update v3.4 (8 Okt 2026) — efisiensi sumber (berdasarkan log run produksi pertama)

Run produksi 8 Okt: 1.402 mentah → 45 tersimpan → 7 notifikasi ✅. Tapi terlihat
pemborosan besar: **Remotive menyumbang 578 "lowongan" yang sebenarnya cuma 17 job
unik** — server Remotive kini mengabaikan parameter `search` (33 query berbeda
semuanya dibalas 17 lowongan terbaru yang sama; ~560 duplikat dibuang dedup setiap run).

- **Remotive per-query dihapus** — feed penuh tetap dipanggil sekali (hasilnya identik,
  hemat 33 panggilan HTTP + ±17 detik per run).
- **JSearch naik dari 2 → 3 query rotasi/hari** (env `JSEARCH_QUERIES_PER_RUN`, default 3):
  setelah Remotive kehilangan kemampuan search, JSearch adalah satu-satunya pencarian
  tertarget. Kuota tetap aman: ±90 call/bulan dari 500.
- Sleep antar-query pencarian 0.5s → 0.3s (beban sumber berkurang).

---

## Update v3.5 (8 Okt 2026) — alert kegagalan run

Tool ini jalan tanpa pengawasan (cron harian). Kalau sebuah run GAGAL (error kode,
Supabase down, secrets keliru, dsb.), sebelumnya tidak ada yang tahu — Telegram hanya
sunyi, tidak bisa dibedakan dari "hari ini tidak ada match".

- Step baru di `daily_hunt.yml`: **"Alert on failure"** (`if: failure()`) — mengirim
  pesan 🚨 ke Telegram berisi link langsung ke log run yang gagal.
- Memakai secrets Telegram yang sudah ada; tidak ada secret/env baru.
- Kalau step alert-nya sendiri gagal, tidak memicu error berantai (`|| true`).
