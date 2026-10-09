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

---

## Update v3.6 (9 Okt 2026) — We Work Remotely dinonaktifkan (account wall)

Kasus nyata: lowongan skor **90** (Software Developer AI Coding — STEUART NUTRITION,
🌍 Worldwide, $90–120k) masuk Telegram, tapi saat dibuka **tidak bisa dilamar** —
halaman WWR kini meminta "Create an account to view full job details" (berbayar
menurut pengalaman user). WWR menyumbang ~48% volume mentah (413 dari 853) —
notifikasi darinya berisiko jadi dead-end yang merebut slot Top-15.

- **WWR OFF secara default** (`ENABLE_WWR` env / repo variable; default kosong = off).
  Log akan menampilkan `We Work Remotely: DILEWATI (account wall...)`.
  Aktifkan lagi bila kamu punya/punya-akan akun WWR: GitHub repo → Settings →
  Secrets and variables → Actions → **Variables** → tambah `ENABLE_WWR` = `1`.
- **Label sumber 📡 di pesan Telegram** (notifier): setiap lowongan kini menampilkan
  asal board-nya (RemoteOK/Himalayas/JSearch/HN...) — dead-end seperti ini langsung
  kelihatan tanpa harus klik linknya dulu.
- Dampak volume: mentah ~853 → ~440/run, tapi **semua yang tersisa bisa dilamar**.
  Lowongan yang cross-post (ada di WWR DAN board lain) tetap tertangkap lewat board
  lain — dedup judul+perusahaan justru otomatis memilih URL dari sumber yang terbuka.
- Tips manual: lowongan WWR sering di-mirror lengkap (termasuk JD penuh & link asli)
  di theohub.global / jobleads — bisa dipakai untuk MEMBACA JD walau apply-nya
  lewat situs perusahaan langsung.

---

## Update v3.7 (9 Okt 2026) — Apply Route Resolver (fase D.5)

Otomatisasi dari "penyelamatan manual" kasus STEUART NUTRITION (skor 90, link WWR
bertembok akun berbayar, jalur alternatif ditemukan lewat situs perusahaan).

Modul baru `resolver.py`, dipanggil `notifier.py` HANYA untuk top ±10 lowongan:
1. **Klasifikasi link apply** — fast-path domain bertembok (WWR/FlexJobs/dkk.) +
   probe HTTP (marker "create an account to view", 401/403/404).
2. **Ekstraksi situs perusahaan** dari deskripsi (format WWR "URL: https://...").
3. **Probe halaman karir** — /careers, /jobs, /apply, dll. + deteksi ATS
   (Lever, Greenhouse, Ashby, BambooHR, Workable, ...) → link daftar lowongan resmi.
4. **Email kontak** — mailto dari /contact perusahaan (jalur direct-apply).
5. **Cross-post** — query JSearch `"judul" perusahaan` (maks 3 call/run) → link
   lowongan yang sama di board lain.

Hasilnya dirender di pesan Telegram:
`⚠️ Link utama butuh akun/berbayar — jalur alternatif: 🏢 halaman karir | 📧 email | 🔁 cross-post`.

Angka-angka pengaman (env): `RESOLVE_APPLY_LINKS` (on/off), `RESOLVE_MAX_JOBS=10`,
`RESOLVE_MAX_PROBES=6`, `RESOLVE_MAX_JSEARCH=3`. Tanpa perubahan schema Supabase.
Workflow: step Notifier kini menerima `RAPIDAPI_KEY` + `RESOLVE_APPLY_LINKS` (vars).

Batasan jujur: halaman karir full-JavaScript tidak terbaca `requests` (dilaporkan apa
adanya, tidak dikarang); situs yang memblokir bot → status `unknown`; kasus rumit
multi-hop tetap paling baik lewat analisis manual. Kuota JSearch total ±180/500 per
bulan (90 ingest + maks 90 resolver) — tetap aman.

---

## Update v3.9 (9 Okt 2026) — "bentuk sempurna": rotasi berkeadilan, skor kembar, JD penuh di Telegram

### 1. Rotasi JSearch berslot (memperbaiki bias vertikal)
Keluhan nyata: "hari ini Telegram isinya hampir semua finance". Penyebab: rotasi
berurutan v3.4 bisa menjatuhkan 3/3 query harian ke satu track (9 Okt: 2/3 finance;
10 Okt: 3/3 finance), sementara technical hanya datang sebagai "banjir" bulanan/mingguan
(HN, WWR) yang langsung habis dimakan memori dedup. v3.9 mengganti rotasi dengan
**4 slot terjamin harian**: 2 query ai_automation (offset berbeda) + 1 query keluarga
management (ops/finance/crm/cs berputar) + 1 query long-tail berputar. Kuota ±120
call/bulan dari 500 free tier (24% — aman). Log kini mencetak `JSearch slot v3.9: [...]`.

### 2. Skor kembar skill_fit × deal_fit + knockouts (usul evaluasi #3)
Prompt juri kini wajib memisah: **skill_fit** (kecocokan teknis/domain) dan
**deal_fit** (kelayakan deal: region, level, yurisdiksi, kompensasi, bahasa),
plus daftar **knockouts**. Skor akhir = min(skill, deal); ada knockout → dipatok 25.
Telegram menampilkan `(skill X • deal Y)` dan baris ⛔ per knockout — deal-breaker
tidak lagi bersembunyi di balik satu angka.

### 3. Dokumen JD harian via Telegram (usul evaluasi #6)
Setiap run yang mengirim lowongan juga mengirim **file .md** berisi JD penuh +
semua jalur apply (utama/karir/email/cross-post) + skor + knockout per lowongan.
Chat lamaran tidak perlu lagi scraping halaman ber-403/berbayar.

### 4. Kesegaran posting (usul evaluasi #5)
Kolom baru `daily_jobs.posted_at` (**migration_v3.sql** — jalankan sekali di Supabase
SQL Editor; ingest punya fallback otomatis bila belum). Notifier melabeli:
❔ tanggal tak diketahui (mirror agregator) / ⚠️ berumur ≥14 hari.

### 5. Kompensasi & junior (lanjutan v3.8)
Tanpa perubahan — knockout QB/Xero, lantai US$2.000, dan judul junior tetap aktif.

---

## Update v3.8 (9 Okt 2026) — lapis knockout terikat profil + kejujuran region & kompensasi

Lahir dari `EVALUASI_TOOL_3_LEAD_BOOKKEEPER.md` (chat asisten lamaran): 3 lead
bookkeeper berskor 65-85 dengan tag 🌍 ternyata NO-GO semua saat JD asli dibaca —
QuickBooks/Xero wajib, inti kepatuhan pajak AS, part-time 10 jam/minggu (≈US$800-
1.400/bln < lantai), level junior US$40K untuk profil 20+ tahun, posting 6 bulan basi.

Perbaikan deterministik (sebelum embedding & skoring, menghemat kuota):
1. **`CANDIDATE_KNOCKOUTS` di tracks.py** (config, editable): istilah wajib
   QuickBooks/Xero/MYOB per-kalimat dengan konteks "required/must/solid/power user/..."
   (pelembut "a plus/preferred" membatalkan), serta klaster kepatuhan AS
   (payroll tax, sales tax, 401k, W-2, 1099, tax preparation, ...) — knockout bila
   ada konteks kata kerja ATAU ≥3 istilah berbeda dalam satu lowongan.
   Funnel counter baru: `knockout_profil`.
2. **Kalkulasi penghasilan** (`filters.estimate_monthly_usd`): parse rate jam/tahun +
   jam/minggu dari JD → estimasi take-home bulanan; HI di bawah `MIN_MONTHLY_USD`
   (default 2000) = dibuang (`kompensasi_dibawah_lantai`). Bonus/equity/sign-on diabaikan.
3. **Judul junior/entry/intern/trainee/graduate ditambahkan ke EXCLUDE_TITLE_TERMS**
   (overqualification + gaji di bawah lantai adalah paket yang sama).
4. **Region jujur (main.py):** klaim LLM `worldwide` wajib bersaksi di TEKS JD
   (worldwide/anywhere/global/apac/...); bila tidak → `unclear` → notifier menampilkan
   ❔ "Region belum jelas", bukan 🌍. JD = sumber kebenaran, bukan metadata agregator.
5. **Transparansi di Telegram (notifier):** baris 💰 estimasi US$/bln + jam/minggu
   dari JD, dan ⚠️ part-time tipis (<20 jam/minggu).
6. **Query beracun dibuang:** `Bookkeeper` keluar dari query track finance_ops
   (vertical bookkeeper AS tertutup struktural untuk profil ini: 3/3 lead mewajibkan
   QB/Xero) — diganti `Finance Operations`.

Yang DITUNDA ke v3.9 (butuh perubahan schema/prompt): skor skill vs deal terpisah
di prompt LLM + daftar knockout terpicu; dokumen JD penuh harian via Telegram
(batas 4096 karakter membuat teks JD tidak muat di pesan); kolom `posted_at` di
daily_jobs supaya lowongan mirror tanpa tanggal bisa dilabeli "stale" (kini umur
>21 hari sudah dibuang HANYA bila tanggal diketahui).
