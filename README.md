# 🧭 AI Career Architect

Personal passive job-hunting automation. Scans global remote job boards daily, filters
out junk (region-locked, foreign-language-required, scams, senior-only), matches the rest
against your profile using vector similarity, then has an LLM act as a recruiter to score
each job and explain *why* it fits — delivered to Telegram.

**Human-in-the-loop by design: this tool never auto-applies.** It shortlists; you decide.

## Pipeline (4 phases)

| Phase | File | What it does |
|---|---|---|
| A. Knowledge (manual) | `knowledge_builder.py` | Extract text from your resume/project PDFs → embed → store in `user_knowledge` |
| B. Ingest (daily) | `ingest.py` | Pull jobs from 9 free sources → cheap filters → route to tracks → embed → similarity gate → `daily_jobs` |
| C. Reasoning (daily) | `main.py` | For each new job: vector-search your knowledge → Gemini scores 0–100 + match reasons + skill gap + interview talking points |
| D. Notify (daily) | `notifier.py` | Top jobs (score ≥ threshold) → formatted Telegram message; sends a status message even when nothing qualifies |

Job sources (all free, only JSearch needs a key): Himalayas, Jobicy, RemoteOK, Arbeitnow,
We Work Remotely (main RSS + 5 category feeds), Remotive, Working Nomads, n8n Community (RSS),
Hacker News "Who's Hiring" (monthly thread via Algolia), JSearch/RapidAPI (rotated daily queries).

## Setup (new installation)

1. **Supabase** (free tier): create project → SQL Editor → run [`migration_v2.sql`](migration_v2.sql)
2. **Dependencies**: `pip install -r requirements.txt` (Python 3.10+)
3. **Config**: copy `.env.example` → `.env`, fill in the values
4. **Knowledge base**: `python knowledge_builder.py resume.pdf profile "Your Name - Profile"`
5. **Health check**: `python db.py`
6. **Dry run** (no quota used, prints the filter funnel): `python ingest.py --dry-run`
7. **Full run**: `python ingest.py && python main.py && python notifier.py`

## Scheduling

The GitHub Actions workflow (`.github/workflows/daily_hunt.yml`) is `workflow_dispatch`-only
on purpose — trigger it from an external scheduler (e.g. cronjob.org) or add a `schedule:`
cron yourself. Daily at 07:00–08:00 local time works well.

## Tuning

- **`tracks.py`** — the only file you need to edit to change target fields:
  profile texts, search queries, keywords, enable/disable tracks.
- `SIMILARITY_THRESHOLD` (default 0.52) — vector gate strictness.
- `MIN_NOTIFY_SCORE` (default 50) — LLM score needed to reach Telegram.
- `MAX_JOBS_TO_EMBED` / `MAX_JOBS_TO_REASON` — per-run budget caps (Gemini free tier).
- `DISABLED_SOURCES` — comma-separated source names to skip.
- `EXCLUDE_TITLE_TERMS` in `tracks.py` — title keywords to always skip.

## Security notes

- Never commit `.env` (already gitignored). In CI, use GitHub Secrets.
- Gemini daily quotas (RPD) are tracked in the DB (`api_usage`, Pacific-time date) so
  multiple runs per day can't exhaust the free tier silently.
- Before publishing this repo publicly: rotate any key that was ever committed, and
  consider squashing history (old commits may contain personal files).

## Design docs

- [`AI_Career_Architect_Context.md`](AI_Career_Architect_Context.md) — original blueprint ("project bible")
- [`UPGRADE_V3.md`](UPGRADE_V3.md) — v3 changelog: sources, filters, thresholds (in Indonesian)

---

## Author

**Orie Grenitho** — AI Solutions & Automation Developer (Indonesia, UTC+7, open to remote worldwide).
Business operator turned software builder: 20+ years in operations, finance and project
management; since 2024 building custom ERPs, internal tools and AI automation pipelines
(Python, JavaScript, React, Node.js, PostgreSQL, n8n, LLM APIs).

- 💼 [LinkedIn](https://www.linkedin.com/in/grenitho) &nbsp;•&nbsp; 🐙 [GitHub](https://github.com/grenitho) &nbsp;•&nbsp; ✉️ grenitho@gmail.com
- 🎬 Project demos: [ALIEN — custom ERP & business automation](https://youtu.be/bQ2vRLY1VKE) • [Orion — AI coding assistant](https://youtu.be/1eYs0uhrR1c) • [Vibe-Pet — desktop app](https://youtu.be/eVbSrh3HToo)
- 🛠️ Other projects: [Text2Vox — API-key-free TTS web app](https://github.com/grenitho/Text2Vox) • [StudioPic — AI mini photo studio](https://github.com/grenitho/StudioPic)
