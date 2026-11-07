# PlacementSync — Intelligent Placement Information Management System

> Automate placement record entry from coordinator emails with human verification,
> Excel register, and analytics dashboard.

![PlacementSync](https://img.shields.io/badge/status-production--ready-green)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.115-green)
![React](https://img.shields.io/badge/react-18-blue)
![Tests](https://img.shields.io/badge/tests-66%20passing-brightgreen)

## What PlacementSync does

A college placement coordinator sends emails announcing student selections at different companies. Instead of manually reading emails and updating Excel, PlacementSync:

1. **Reads** placement-related emails (`.eml` upload or Gmail API OAuth 2.0)
2. **Classifies** each email (selection, shortlisting, interview, offer letter, general, unrelated)
3. **Extracts** structured info — company, student names, reg numbers, branches, roles, CTC/packages, dates
4. **Downloads & parses attachments** (PDF/DOCX) and includes them in extraction
5. **Displays** extracted info for **human verification** — nothing is recorded without approval
6. **Saves** approved records to a SQLite database (PostgreSQL-swappable)
7. **Updates** an Excel placement register (append-only, duplicate-safe)
8. **Shows** a dashboard with charts (branch-wise, company-wise, package distribution)
9. **Tracks** every change in an audit log
10. **Backs up** the database and Excel register on demand

## Core principles

- **Human approval is mandatory.** Uncertain extraction results never enter the official register silently.
- **Works without AI APIs.** Extraction is deterministic, rule-based, and auditable. No paid AI required.
- **Read-only w.r.t. Gmail.** The system only reads emails — it never sends, deletes, or modifies them.
- **Never hardcode secrets.** OAuth credentials and tokens come from environment variables; tokens are encrypted at rest.
- **Modular architecture.** SQLite today, PostgreSQL tomorrow — change one config value.

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0, SQLite |
| Validation | Pydantic 2 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Charts | Recharts |
| Email parsing | Python stdlib `email`, BeautifulSoup 4 |
| PDF extraction | pdfplumber (PyPDF2 fallback) |
| DOCX extraction | python-docx |
| Gmail API | google-api-python-client, google-auth, google-auth-oauthlib |
| Token encryption | cryptography (Fernet) |
| Excel | pandas, openpyxl |
| Tests | pytest (66 passing) |

## Project structure

```
placement-sync/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # auth, backup, emails, excel, extraction, gmail, records, audit
│   │   ├── core/             # config, database, logging, security
│   │   ├── models/           # SQLAlchemy models (7 tables)
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # classification, email, excel, extraction, gmail, attachment
│   ├── tests/                # 66 tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, Inbox, Review, Register, Settings, Audit, Backup
│   │   ├── components/       # Layout, Panel
│   │   ├── services/         # Axios API client
│   │   └── types/            # TypeScript types
│   └── package.json
├── sample_emails/            # Fictional .eml files for testing
├── docs/
│   └── architecture.md       # Detailed architecture & design decisions
├── .env.example              # Copy to .env and configure
├── .gitignore
└── README.md
```

## Screenshots / Pages

| Page | Purpose |
|------|---------|
| **Dashboard** | Placement statistics, Recharts charts (branch, company, package), filters |
| **Email Inbox** | Upload `.eml` or fetch from Gmail, view processing status |
| **Review Queue** | Original email + extracted students, approve/edit/reject |
| **Placement Register** | Searchable table of approved records, Excel export |
| **Settings** | Academic year, Excel path, Gmail connection |
| **Audit Log** | Change history, summary counts by table/action |
| **Backup** | Database & Excel backup download, restore instructions |

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 18+ and npm

### 1. Clone

```bash
git clone https://github.com/JosephJonathanFernandes/placementsync-mis.git
cd placementsync-mis
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
# Edit .env and set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET if using Gmail
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend creates `placement_sync.db` on first start and exposes the API at `http://127.0.0.1:8000`. Visit `http://127.0.0.1:8000/health` to confirm it's running.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api to backend)
npm run build        # production build
```

The dev server proxies `/api` to `http://127.0.0.1:8000`.

## Running the tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

**66 tests passing** covering classification, extraction (paragraphs, bullets, HTML tables, forwarded emails, missing fields), Excel generation, database insertion, duplicate detection, approval workflow, audit logs, backup, and error handling.

## Gmail OAuth setup (Phase 2+)

1. Create a Google Cloud project and OAuth 2.0 credentials (Web application).
2. Add `http://localhost:8000/api/auth/gmail/callback` as an authorized redirect URI.
3. Copy `.env.example` to `.env` and set:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
4. Start the backend, go to **Settings → Connect Gmail account**, and authorize.

The app requests only `gmail.readonly` — it never sends, deletes, or modifies emails.

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/emails/upload` | Upload `.eml` file |
| `GET` | `/api/emails` | List emails |
| `POST` | `/api/extraction/run/{id}` | Run extraction on an email |
| `GET` | `/api/extraction/pending` | List pending review results |
| `POST` | `/api/extraction/{id}/approve` | Approve extraction (writes to DB) |
| `POST` | `/api/extraction/{id}/reject` | Reject extraction |
| `GET` | `/api/records` | List approved placement records |
| `GET` | `/api/records/stats` | Dashboard statistics with filters |
| `GET` | `/api/excel/export` | Download placement register Excel |
| `GET` | `/api/auth/gmail/authorize` | Get OAuth URL |
| `GET` | `/api/auth/gmail/status` | Gmail connection status |
| `POST` | `/api/auth/gmail/disconnect` | Disconnect Gmail |
| `GET` | `/api/gmail/messages` | List placement-related Gmail messages |
| `POST` | `/api/gmail/process` | Fetch & process new Gmail messages |
| `GET` | `/api/audit` | Audit log entries |
| `POST` | `/api/backup/database` | Download DB backup |
| `POST` | `/api/backup/excel` | Download Excel backup |

## Sample emails

`sample_emails/` contains fictional `.eml` files covering:

- `selection_simple.eml` — simple paragraph, two students
- `selection_bullets.eml` — bullet list with reg numbers & branches
- `selection_html_table.eml` — HTML table with two students
- `forwarded_selection.eml` — forwarded selection announcement
- `shortlist_only.eml` — shortlisted candidates (correctly NOT approvable)

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for detailed design decisions, data flow, database schema, and limitations.

## Roadmap

- [x] Phase 1 — MVP: `.eml` upload, extraction, review, Excel
- [x] Phase 2 — Gmail OAuth & automatic email processing
- [x] Phase 3 — PDF/DOCX attachment extraction
- [x] Phase 4 — Dashboard analytics with Recharts
- [x] Phase 5 — Audit logs, backup/recovery, error handling, 66 tests
- [ ] Phase 6 — PostgreSQL support, multi-user auth, deployment guide

## License

Internal college placement tool — no license specified.

---

**PlacementSync** — Automate data entry, not blind trust. Every placement record is human-verified before it enters the official register.