-- ============================================================================
-- migration_v3.sql — v3.9: kolom tanggal posting untuk label kesegaran
-- ============================================================================
-- Jalankan SEKALI di Supabase Dashboard -> SQL Editor.
-- AMAN: bila belum dijalankan, ingest tetap jalan (db.save_daily_job punya
-- fallback otomatis tanpa kolom ini).

alter table if exists daily_jobs
  add column if not exists posted_at date;

create index if not exists idx_daily_jobs_posted_at
  on daily_jobs (posted_at);
