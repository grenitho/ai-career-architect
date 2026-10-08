-- ============================================================================
-- migration_v2.sql — Schema lengkap AI Career Architect (direkonstruksi di v3)
-- ============================================================================
-- HANYA jalankan ini untuk project Supabase BARU / pemulihan.
-- Database yang sudah jalan TIDAK perlu di-migrate ulang (file ini direkonstruksi
-- dari pemakaian nyata di db.py supaya repo punya cetak biru yang lengkap).
-- Jalankan lewat Supabase Dashboard -> SQL Editor.

create extension if not exists vector;

-- ----------------------------------------------------------------------------
-- user_knowledge : profil/CV/dokumen proyek (konteks RAG untuk deep reasoning)
-- ----------------------------------------------------------------------------
create table if not exists user_knowledge (
  id serial primary key,
  type text,                 -- 'profile' | 'cv' | 'project_doc' | 'project_video_summary'
  title text,
  text_content text,
  asset_url text,
  embedding vector(768),     -- dimensi Gemini embedding (di-truncate ke 768 di ai_engine)
  created_at timestamptz default now()
);

-- ----------------------------------------------------------------------------
-- daily_jobs : lowongan yang lolos filter + hasil analisis
-- ----------------------------------------------------------------------------
create table if not exists daily_jobs (
  id serial primary key,
  job_title text,
  company text,
  description text,
  apply_url text,
  match_score int default 0,
  ai_reasoning jsonb default '{}'::jsonb,
  processed_date date default current_date,
  embedding vector(768),
  analyzed boolean default false,
  notified boolean default false,
  track text,                -- nama bidang dari tracks.py
  source text,               -- asal lowongan (RemoteOK, Himalayas, ...)
  similarity float,          -- cosine similarity vs profile_text track
  location_note text,        -- catatan filter region
  created_at timestamptz default now()
);

create index if not exists idx_daily_jobs_unanalyzed
  on daily_jobs (analyzed, similarity desc);
create index if not exists idx_daily_jobs_notified
  on daily_jobs (notified, match_score desc);
create index if not exists idx_daily_jobs_processed
  on daily_jobs (processed_date);

-- ----------------------------------------------------------------------------
-- seen_jobs : memori lintas-run supaya lowongan tidak dinilai dua kali
-- ----------------------------------------------------------------------------
create table if not exists seen_jobs (
  job_key text primary key,  -- URL ternormalisasi ATAU judul_perusahaan (lowercase)
  outcome text,              -- 'saved' | 'low_similarity'
  similarity float,
  last_seen date default current_date
);

create index if not exists idx_seen_jobs_last on seen_jobs (last_seen);

-- ----------------------------------------------------------------------------
-- track_profiles : cache embedding profile_text tiap bidang
-- ----------------------------------------------------------------------------
create table if not exists track_profiles (
  name text primary key,
  text_hash text,            -- sha256(profile_text)[:16]; berubah -> re-embed
  embedding vector(768),
  updated_at timestamptz default now()
);

-- ----------------------------------------------------------------------------
-- api_usage : counter kuota harian Gemini (reset mengikuti tanggal Pasifik)
-- ----------------------------------------------------------------------------
create table if not exists api_usage (
  usage_date date primary key,
  embedding_calls int default 0,
  reasoning_calls int default 0
);

-- ----------------------------------------------------------------------------
-- RPC untuk vector search (dipanggil db.find_relevant_knowledge)
-- ----------------------------------------------------------------------------
create or replace function match_user_knowledge(
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
returns table (
  id int,
  type text,
  title text,
  text_content text,
  asset_url text,
  similarity float
)
language sql stable
as $$
  select
    uk.id,
    uk.type,
    uk.title,
    uk.text_content,
    uk.asset_url,
    1 - (uk.embedding <=> query_embedding) as similarity
  from user_knowledge uk
  where uk.embedding is not null
    and 1 - (uk.embedding <=> query_embedding) > match_threshold
  order by uk.embedding <=> query_embedding
  limit match_count;
$$;
