"""Konfigurasi bidang pencarian (TRACKS). Ini satu-satunya file yang perlu Anda edit
untuk menambah/mengurangi/mengubah bidang yang dicari.

Tiap track punya:
  label / emoji       : tampilan di Telegram
  enabled             : False = dilewati sepenuhnya
  profile_text        : teks (bahasa Inggris) yang di-embed, mewakili "kandidat ideal
                        untuk bidang ini". Dibandingkan dengan deskripsi lowongan.
                        PENTING: tulis hanya hal yang benar-benar Anda kuasai. Teks ini
                        menentukan lowongan mana yang lolos.
  queries             : judul posisi (maks 3 kata) untuk sumber yang menerima pencarian
  title_terms         : kata di JUDUL lowongan yang menandakan bidang ini
  skill_terms         : kata di judul/deskripsi yang menandakan bidang ini
  min_hits_with_title : jumlah skill_terms minimal bila judul sudah cocok (default 1)
  min_hits            : jumlah skill_terms minimal bila judul tidak cocok (default 3)
  threshold           : (opsional) ambang cosine similarity khusus track ini;
                        kosong = pakai SIMILARITY_THRESHOLD dari .env (default 0.52)

V3 ( Okt 2026 ):
  - Track BARU: ops_pm, finance_ops, cs_success (sesuai target kerja: management boleh,
    tidak harus IT, per-proyek boleh, syarat mutlak 100% remote).
  - min_hits diturunkan (4->3) untuk track yang terlalu sempit: corong v2 membuang
    ~90 lowongan/hari di tahap "tidak_ada_bidang".
  - MAX_QUERIES_PER_TRACK naik 2->3 (di ingest.py) supaya pencarian per-query lebih luas.
  - CANDIDATE_NOTES diperbarui sesuai narasi yang benar: Logaritma Danapati = karyawan
    (Finance Manager); selain itu usaha sendiri.
"""

TRACKS = {
    "ai_automation": {
        "label": "AI & Automation",
        "emoji": "🤖",
        "enabled": True,
        "profile_text": (
            "AI automation and workflow developer. Builds web apps and internal tools "
            "with generative AI, Python, JavaScript, React, Node, PostgreSQL, Supabase, "
            "n8n, Make, Zapier, webhooks and LLM APIs. Has shipped a custom ERP/CRM for "
            "an automotive dealership (task management for a 20-person team, 80,000+ "
            "sales/service records, n8n pipelines turning raw data into daily reports), "
            "an educational app, and utility/desktop apps. Looking for AI automation, "
            "no-code or low-code, workflow automation, prompt engineering or AI app "
            "development work, including freelance and per-project contracts."
        ),
        "queries": ["AI Automation Specialist", "No-Code Automation", "Python Developer"],
        "title_terms": [
            "ai", "automation", "no-code", "nocode", "low-code", "workflow", "n8n",
            "zapier", "llm", "prompt", "chatbot", "python", "full stack", "fullstack",
            "web developer", "react", "node", "ai engineer", "ai developer",
            "automation engineer", "ai specialist", "ai consultant",
            "forward deployed", "solutions engineer",
        ],
        "skill_terms": [
            "python", "javascript", "typescript", "react", "node", "nodejs",
            "postgresql", "supabase", "n8n", "zapier", "make.com", "webhook",
            "webhooks", "api", "llm", "openai", "gemini", "claude",
            "prompt engineering", "rag", "automation", "no-code", "low-code", "airtable",
        ],
        "min_hits": 3,
    },
    "ops_pm": {
        "label": "Operations & Project Mgmt",
        "emoji": "📋",
        "enabled": True,
        "profile_text": (
            "Operations and project manager with 20+ years of experience running "
            "businesses end to end. Owned P&L, supply chain, procurement, logistics and "
            "vendor negotiation for a commodities trading company. Managed finance, "
            "budgeting, cost control and cross-functional teams for a digital media "
            "company. Delivered 20+ infrastructure and real-estate projects on time and "
            "on budget, leading contractor teams of up to 25. Also builds business "
            "software: deployed a custom ERP (CRM, task management for a 20-person team, "
            "inventory and reporting over 80,000+ records) and n8n/Python automation "
            "pipelines. Looking for remote operations manager, business operations, "
            "program manager, project manager, process improvement or implementation "
            "roles, including contract and per-project work."
        ),
        "queries": ["Operations Manager", "Project Manager", "Business Operations"],
        "title_terms": [
            "operations manager", "operations lead", "ops manager", "business operations",
            "bizops", "project manager", "program manager", "project coordinator",
            "operations coordinator", "operations analyst", "process improvement",
            "implementation manager", "implementation consultant", "technical project",
            "technical program", "chief of staff", "scrum master", "delivery manager",
            "operations specialist", "project management", "project management officer",
            "pmo",
        ],
        "skill_terms": [
            "project management", "operations", "stakeholder", "vendor", "procurement",
            "supply chain", "logistics", "budget", "forecast", "kpi", "okr", "sop",
            "process improvement", "cross-functional", "roadmap", "timeline",
            "risk management", "agile", "kanban", "scrum", "jira", "asana", "notion",
            "erp", "crm", "reporting", "coordination", "onboarding", "workflow",
            "automation", "resource planning", "pmp", "delivery",
        ],
        "min_hits": 3,
    },
    "finance_ops": {
        "label": "Finance & Accounting",
        "emoji": "💰",
        "enabled": True,
        "profile_text": (
            "Finance manager with hands-on experience directing financial planning, "
            "budgeting, cash-flow management, cost control and operational reporting for "
            "a digital media company partnered with Alibaba Group (WeMedia), plus full "
            "P&L ownership of trading and construction businesses. Comfortable with "
            "vendor negotiation, invoicing, bookkeeping workflows and spreadsheet "
            "modeling, and builds his own automation tools (Python, SQL, n8n) for "
            "reporting and reconciliation. Looking for remote finance manager, financial "
            "analyst, bookkeeper, accounts payable/receivable or finance operations "
            "roles, including contract work."
        ),
        "queries": ["Finance Manager", "Financial Analyst", "Finance Operations"],
        "title_terms": [
            "finance manager", "financial analyst", "finance analyst", "bookkeeper",
            "accounting", "accountant", "accounts payable", "accounts receivable",
            "finance operations", "financial controller", "payroll", "billing",
            "controller", "finance associate", "ap/ar",
        ],
        "skill_terms": [
            "bookkeeping", "general ledger", "reconciliation", "accounts payable",
            "accounts receivable", "invoicing", "billing", "payroll", "quickbooks",
            "xero", "excel", "financial reporting", "budgeting", "forecasting",
            "cash flow", "cost control", "audit", "gaap", "ifrs", "journal entries",
            "month-end", "variance analysis", "sql", "erp", "finance",
        ],
        "min_hits": 3,
    },
    "crm_ops": {
        "label": "CRM & Sales Ops",
        "emoji": "📇",
        "enabled": True,
        "profile_text": (
            "CRM and sales operations specialist. Designs and configures CRM and task "
            "management systems, sales pipelines, lead follow-up workflows, reporting "
            "dashboards and process automation for sales teams. Built a custom CRM and "
            "ERP for an automotive dealership: task management for a 20-person team and "
            "reporting over 80,000+ sales/service records, with n8n pipelines producing "
            "daily filtered reports. Familiar with HubSpot, Zoho, Salesforce or "
            "Pipedrive style tools. Looking for CRM administrator, sales operations or "
            "business operations roles."
        ),
        "queries": ["CRM Specialist", "Sales Operations", "CRM Administrator"],
        "title_terms": [
            "crm", "hubspot", "salesforce", "zoho", "pipedrive", "sales operations",
            "sales ops", "revenue operations", "revops", "business operations",
            "operations coordinator", "operations analyst",
        ],
        "skill_terms": [
            "crm", "hubspot", "salesforce", "zoho", "pipedrive", "pipeline",
            "lead management", "sales operations", "reporting", "dashboard",
            "workflow", "automation", "onboarding", "zapier", "airtable", "notion",
            "process improvement",
        ],
        "min_hits": 3,
    },
    "cs_success": {
        "label": "Customer Success",
        "emoji": "🤝",
        "enabled": True,
        "profile_text": (
            "Customer-facing operations generalist from a small-business background: "
            "order handling, logistics and parcel dispatch, vendor and customer "
            "negotiation, CRM data management and after-sales follow-up across trading, "
            "logistics and retail businesses. Built and deployed the CRM and "
            "task-management system used daily by a 20-person dealership team to track "
            "customers, sales and service (80,000+ records). Bilingual Indonesian and "
            "English. Looking for remote customer success manager, customer success "
            "associate, account manager, customer operations or client services roles."
        ),
        "queries": ["Customer Success Manager", "Customer Success", "Account Manager"],
        "title_terms": [
            "customer success", "cs manager", "account manager", "customer operations",
            "customer experience", "client success", "customer support",
            "support specialist", "customer service", "client services", "cx",
        ],
        "skill_terms": [
            "customer success", "onboarding", "retention", "churn", "renewal", "upsell",
            "crm", "zendesk", "intercom", "freshdesk", "hubspot", "salesforce",
            "ticket", "sla", "customer satisfaction", "csat", "nps", "escalation",
            "relationship", "client", "support", "communication", "problem solving",
        ],
        "min_hits": 3,
    },
    "construction": {
        "label": "Construction & Estimating",
        "emoji": "🏗️",
        "enabled": True,
        "profile_text": (
            "Construction estimator and project coordinator with hands-on background "
            "as a building contractor and property developer. Experience with cost "
            "estimation, bills of quantities, quantity takeoff, project progress "
            "tracking, subcontractor coordination, and land plot and subsidized "
            "housing development. Looking for remote construction estimating, "
            "takeoff, cost control or project coordination work."
        ),
        "queries": [
            "Construction Estimator", "Quantity Surveyor", "Construction Coordinator",
        ],
        "title_terms": [
            "estimator", "estimating", "quantity surveyor", "takeoff", "take-off",
            "construction", "project coordinator", "cost engineer", "civil",
        ],
        "skill_terms": [
            "estimating", "estimator", "takeoff", "take-off", "quantity",
            "bill of quantities", "boq", "construction", "bluebeam", "procore",
            "planswift", "autocad", "revit", "cost control", "subcontractor",
            "scheduling", "civil", "contractor",
        ],
        "min_hits": 3,
    },
    "content_ops": {
        "label": "Content & Social Media",
        "emoji": "🎬",
        "enabled": True,
        "profile_text": (
            "Content operations and social media specialist. Has supplied content "
            "for a media partner and built AI tools that generate social media and "
            "YouTube content. Skilled in content planning, scripting, scheduling, "
            "research, short-form video workflows and channel management. Looking for "
            "content operations, social media, scriptwriting or YouTube channel roles."
        ),
        "queries": ["Content Operations", "Social Media Specialist", "YouTube Scriptwriter"],
        "title_terms": [
            "content", "social media", "youtube", "video editor", "copywriter",
            "scriptwriter", "script writer", "community manager", "seo",
        ],
        "skill_terms": [
            "content", "social media", "youtube", "instagram", "tiktok",
            "scheduling", "calendar", "script", "copywriting", "seo", "editing",
            "short-form", "analytics", "canva", "capcut", "audience", "engagement",
        ],
        "min_hits": 3,
    },
    "qa_testing": {
        "label": "QA & Testing",
        "emoji": "🧪",
        "enabled": True,
        "profile_text": (
            "QA and product tester for web and mobile apps. Builds web apps end to end "
            "and tests them: manual testing, test cases, bug reports, regression and "
            "user acceptance testing. Looking for QA tester, software tester or "
            "manual QA roles."
        ),
        "queries": ["QA Tester", "Software Tester", "Manual QA"],
        "title_terms": [
            "qa", "tester", "testing", "quality assurance", "test analyst", "uat",
            "usability",
        ],
        "skill_terms": [
            "testing", "test cases", "bug", "regression", "qa", "quality assurance",
            "uat", "jira", "selenium", "cypress", "playwright", "manual testing",
            "test plan",
        ],
        "min_hits": 3,
    },
    "edu_content": {
        "label": "Edu Content",
        "emoji": "📚",
        "enabled": True,
        "profile_text": (
            "Educational content and edtech builder. Created learning apps for "
            "arithmetic and English for school-age children, including exercises, "
            "quizzes and lesson content. Looking for instructional design, curriculum "
            "development, e-learning content or educational content creation roles."
        ),
        "queries": ["Instructional Designer", "Curriculum Developer", "Educational Content"],
        "title_terms": [
            "instructional designer", "curriculum", "educational content",
            "learning content", "course creator", "e-learning", "elearning", "edtech",
            "lesson",
        ],
        "skill_terms": [
            "instructional design", "curriculum", "e-learning", "elearning", "lesson",
            "quiz", "assessment", "learning objectives", "edtech", "course",
            "content creation", "children", "k-12",
        ],
        "min_hits": 3,
    },
    "ai_training": {
        "label": "AI Training (Indonesian)",
        "emoji": "🧠",
        "enabled": True,
        "profile_text": (
            "Native Indonesian speaker experienced with generative AI tools who can "
            "evaluate and rate LLM responses, write prompts, annotate and label data, "
            "and review quality following guidelines. Looking for AI trainer, LLM "
            "evaluator, data annotator or Indonesian language specialist work."
        ),
        "queries": ["AI Trainer Indonesian", "Data Annotator", "LLM Evaluator"],
        "title_terms": [
            "ai trainer", "annotator", "annotation", "data labeling", "rater",
            "evaluator", "ai tutor", "indonesian", "linguist",
        ],
        "skill_terms": [
            "annotation", "labeling", "rlhf", "evaluation", "prompt", "llm",
            "indonesian", "bahasa", "ai training", "quality review", "guidelines",
            "linguist", "translation", "localization",
        ],
        "min_hits": 3,
    },
    "support_va": {
        "label": "Support & Virtual Assistant",
        "emoji": "🎧",
        "enabled": True,
        "profile_text": (
            "Bilingual Indonesian and English customer support and virtual assistant "
            "for companies serving the Indonesian market. Experience running small "
            "businesses including parcel and logistics handling, order handling, CRM "
            "data entry, scheduling and administrative tasks. Looking for customer "
            "support, virtual assistant, data entry or Indonesian market support roles."
        ),
        "queries": ["Virtual Assistant", "Customer Support", "Indonesian Support"],
        "title_terms": [
            "virtual assistant", "customer support", "customer service",
            "customer success", "support specialist", "support agent", "data entry",
            "administrative assistant", "executive assistant", "indonesian",
        ],
        "skill_terms": [
            "customer support", "customer service", "zendesk", "freshdesk",
            "intercom", "chat support", "email support", "data entry", "scheduling",
            "inbox", "calendar", "crm", "indonesian", "bahasa indonesia", "english",
            "ticket",
        ],
        "min_hits": 3,
    },
}

# Kata di JUDUL yang membuat lowongan dilewati. Anda belum punya riwayat kerja sebagai
# karyawan, jadi melamar posisi senior/pimpinan hampir pasti buang waktu. Hapus
# "senior" dari daftar ini kalau Anda mau tetap melihat posisi senior.
EXCLUDE_TITLE_TERMS = [
    "senior", "sr", "principal", "director", "head of", "vp", "vice president",
    "chief", "team lead", "tech lead", "engineering manager", "staff engineer",
    "staff software",
    # v3.8: level junior/entry = buang leverage profil 20+ tahun & gaji di bawah
    # lantai (kasus nyata: "Junior Accountant" US$40K dinilai 65 oleh tool).
    "junior", "jr", "entry level", "entry-level", "intern", "internship",
    "trainee", "graduate", "apprentice",
]

# Dikirim ke Gemini pada tahap analisis (main.py) supaya penilaian tidak bias ke
# "pengalaman kerja formal". V3: narasi dikoreksi sesuai fakta sebenarnya.
CANDIDATE_NOTES = (
    "Kandidat berbasis di Indonesia (UTC+7), mencari kerja 100% REMOTE worldwide "
    "(full-time, kontrak, freelance, maupun per-proyek — semua diterima; tidak ada "
    "posisi yang boleh mengharuskan onsite/hybrid/relokasi). Total 20+ tahun "
    "pengalaman: ~4 tahun sebagai karyawan (Finance Manager di perusahaan digital "
    "media partner Alibaba WeMedia, 2018-2021: budgeting, cost control, pelaporan, "
    "logistik event) dan sisanya memimpin usaha sendiri (direktur perusahaan trading "
    "komoditas lada, kontraktor infrastruktur & real estate dengan 20+ proyek, sewa "
    "LED/sound system event, ekspedisi, air galon). Sejak 2024 membangun software "
    "dengan AI generatif: ERP/CRM custom yang dipakai satu dealer otomotif (task "
    "management tim 20 orang, 80.000+ record sales/service, pipeline n8n untuk "
    "laporan harian), aplikasi edukasi, dan berbagai utility. Nilai kecocokan "
    "berdasarkan bukti nyata di profil, bukan jabatan formal. Jangan menghukum "
    "kandidat karena sebagian besar pengalamannya berwirausaha — itu justru bukti "
    "ownership end-to-end (P&L, vendor, tim, delivery). Bahasa Inggris kandidat "
    "fungsional untuk kerja async (menulis); nilai lowongan yang mengandalkan "
    "presentasi lisan intensif sedikit lebih rendah."
)

# ---------------------------------------------------------------------------
# v3.8: KNOCKOUT TERIKAT PROFIL — dievaluasi SEBELUM embedding & skoring
# (menghemat kuota dan slot notifikasi). Fakta-fakta ini tidak bisa diklaim
# atau dipelajari cepat secara jujur, jadi lowongan yang mewajibkannya adalah
# dead-end sejak lahir. Edit bebas bila kondisi kandidat berubah
# (mis. setelah mengambil sertifikasi QuickBooks).
# Format: (nama_knockout, regex_istilah, regex_konteks_wajib) — keduanya harus
# muncul dalam SATU kalimat, kecuali kalimat mengandung pelembut ("a plus",
# "preferred", ...) yang membuat istilah tidak lagi wajib.
# ---------------------------------------------------------------------------
CANDIDATE_KNOCKOUTS = (
    (
        "software akuntansi wajib (QuickBooks/Xero/MYOB) - kandidat tidak punya",
        r"\b(?:quick\s?books|xero|myob)\b",
        r"\b(?:required|require|must|solid|strong|proficient|power\s+user|expert|"
        r"extensive|daily|hands[- ]on|experienced?\s+(?:with|in|using)|working\s+"
        r"knowledge\s+of|comfortable\s+with)\b",
    ),
    (
        "inti kepatuhan pajak/AS (yurisdiksi yang tidak pernah kandidat kerjakan)",
        r"\b(?:payroll\s+tax|sales\s+tax|use\s+tax|401k|w-2|1099|irs\s+filings?|"
        r"tax\s+preparation|tax\s+filings?|franchise\s+tax|audit\s+requirements?)\b",
        r"\b(?:reconcil\w*|prepar\w*|process\w*|manag\w*|handl\w*|fil\w*|submit\w*|report\w*)\b",
    ),
)
# Tanpa konteks kata kerja pun, >= N istilah kepatuhan AS berbeda di satu lowongan
# sudah cukup untuk knockout (pola daftar tugas panjang, kasus Oasis Wellness).
COMPLIANCE_TERMS_MIN_GLOBAL = 3
