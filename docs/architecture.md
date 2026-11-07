# PlacementSync — Architecture (Phases 1-3)

## Overview

PlacementSync is a full-stack application that extracts student placement
information from placement-coordinator emails and maintains a verified placement
register. Phase 1 delivers the MVP: manual `.eml` upload, rule-based extraction,
human verification, SQLite storage, and Excel export. Phase 2 adds Gmail OAuth
and automatic email fetching. Phase 3 adds PDF/DOCX attachment processing.

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0, SQLite |
| Validation | Pydantic 2 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Email parsing | Python stdlib `email`, BeautifulSoup 4 |
| PDF extraction | pdfplumber (with PyPDF2 fallback) |
| DOCX extraction | python-docx |
| Excel | pandas, openpyxl |
| Gmail API | google-api-python-client, google-auth, google-auth-oauthlib |
| Security | cryptography (Fernet for token encryption at rest) |
| Tests | pytest, pytest-asyncio, httpx |

## Module map (backend)

- `app/core/config.py` — environment-based settings (pydantic-settings)
- `app/core/database.py` — SQLAlchemy engine/session; `create_all()` builds
  all tables. Swapping SQLite for PostgreSQL requires only `DATABASE_URL`.
- `app/core/logging.py` — structured logging to stdout and optional file
- `app/models/` — `Student`, `Company`, `PlacementRecord`, `Email`,
  `ExtractionResult`, `AuditLog`
- `app/schemas/` — Pydantic v2 schemas for API requests/responses
- `app/services/email_service/parser.py` — `.eml` parsing (Subject, From,
  Date, text/plain + text/html bodies, attachments list)
- `app/services/classification_service/classifier.py` — keyword/rule-based
  email classification (offline, no AI)
- `app/services/extraction_service/engine.py` — deterministic extraction of
  company, students, role, CTC, date, status; line-aware, with confidence
  scoring, missing-field reporting, and warnings
- `app/services/excel_service/generator.py` — append-only `.xlsx` register with
  duplicate avoidance
- `app/api/routes/` — FastAPI endpoints: emails, extraction (run/pending/
  approve/reject), records, excel (export/download), stats

## Database schema

- **students(id, name, registration_number UNIQUE, branch, timestamps)**
- **companies(id, name UNIQUE, timestamps)**
- **placement_records(id, student_id, company_id, job_role, package,
  selection_date, status, approval_status, email_id, extraction_result_id,
  timestamps)** — unique constraint on (student_id, company_id, job_role)
  prevents duplicate records; a student may hold multiple offers from different
  companies.
- **emails(id, email_id UNIQUE, subject, sender, body_text, body_html, source,
  received_at, timestamps)**
- **extraction_results(id, email_id, company_name, confidence, review_status,
  extracted_students JSON, raw_extraction JSON, missing_fields JSON, warnings
  JSON, timestamps)**
- **audit_logs(id, table_name, record_id, action, old_values JSON,
  new_values JSON, changed_by, timestamps)**

## Extraction engine design

The engine is intentionally deterministic and auditable:

1. Signature/disclaimer tail is stripped at line-anchored markers
   (`--`, `Regards`, `Placement Cell`, …).
2. Body is processed **line by line** so fields do not bleed across lines.
3. A stateful scanner opens a student record at each `Name:` line and attaches
   subsequent `Reg No`, `Branch`, `Role`, `CTC` lines until the next name.
4. Bullet/numbered lines are parsed for `Name (Reg, Branch) - Role - Package`.
5. HTML tables are mapped by header row (Student Name, Reg No, Branch, Role,
   CTC).
6. Token-level fallback catches names in selection-context lines, but skips
   sentence-style announcements and company/role-looking tokens to avoid false
   positives.

Missing fields are reported, never invented. Names appearing only in
congratulations messages are not treated as selected students. Each extracted
record references its source email.

## Classification rules (Module B)

Categories: `selection_announcement`, `shortlisting_announcement`,
`interview_notification`, `offer_letter_announcement`, `general_placement`,
`unrelated`. Shortlist keywords take priority unless strong selection signals
are present, so shortlisted candidates are never confused with selected ones.
Only `selection_announcement` (and `offer_letter_announcement`, status
`Offered`) records enter the approval workflow; shortlisting results can only
be rejected.

## Human verification (Module D)

Review interface shows: original email, extracted students, company, confidence,
missing fields, and warnings. Actions: approve, edit, reject. Approval runs in
a database transaction: students and companies are looked up/created, placement
records inserted, the extraction result marked approved, and an audit log entry
written. Rejection marks the result rejected and audits it.

## Excel automation (Module F)

`exports/placement_register.xlsx` with columns:
Sr. No., Student Name, Registration No., Branch, Company, Role, CTC, Date,
Status.

The register is append-only: approved records are added without overwriting
existing rows; duplicates (same student + company + role) are skipped; existing
data is never destroyed without explicit `overwrite` confirmation.

## Security

- No Gmail passwords are ever requested.
- No OAuth credentials or API keys are hardcoded.
- Only read-only Gmail scopes (Phase 2).
- Configuration via environment variables; `.env.example` provided, `.env`
  gitignored.

## Frontend

Single-page React app with React Router. Pages: Dashboard, Email Inbox (with
.eml upload), Review Queue (verification + edit + approve/reject), Placement
Register (searchable table + Excel export), Settings. Axios client proxies
`/api` to the FastAPI backend during development.

## Phase 2 — Gmail OAuth and email fetching

### OAuth 2.0 flow

1. **`GET /api/auth/gmail/authorize`** — generates a Google OAuth consent URL
   with `access_type=offline` and `prompt=consent` to ensure a refresh token is
   issued. A short-lived CSRF state token is generated and stored in memory.
2. **User consent** — the frontend redirects the user to Google. The user grants
   the `gmail.readonly` scope only.
3. **`GET /api/auth/gmail/callback`** — Google redirects here with an
   authorization code. The backend verifies the state token, exchanges the code
   for access/refresh tokens via `google-auth-oauthlib`, and stores them
   **encrypted at rest** (Fernet, key derived from `SECRET_KEY`). The backend
   then redirects to the frontend settings page.
4. **`GET /api/auth/gmail/status`** / **`POST /api/auth/gmail/disconnect`** —
   check connection or delete stored credentials.

### Gmail API client (`app/services/gmail_service/client.py`)

- All access uses the `gmail.readonly` scope — the app never sends, deletes, or
  modifies emails.
- Access tokens are automatically refreshed using the stored refresh token via
  `google.auth.transport.requests.Request`.
- `list_messages()` — Gmail `users().messages().list()` with a search query
  (e.g. `selected OR congratulations OR placement ...`), optional label filter,
  and max results.
- `get_message_raw()` — fetches a message in `format=raw` (base64url RFC 2822),
  which is decoded and parsed by the existing `.eml` parser.
- `list_labels()` — lists all Gmail labels for the connected account.

### Automatic processing (`app/services/gmail_service/processor.py`)

`process_new_messages()`:
1. Loads stored credentials (refreshing the access token if expired).
2. Lists messages matching the placement keyword query.
3. For each message:
   - Skips if already stored (deduplication by Gmail message ID).
   - Decodes the raw message and parses it with the Phase 1 `.eml` parser.
   - Stores it as an `Email` record (source = "gmail").
   - Classifies it (Module B).
   - If it is a **selection announcement**, runs the extraction engine and
     creates a pending `ExtractionResult` for human review.

Shortlisted candidates are never treated as selected students. Nothing is
written to the official placement register until a human approves.

### Database model (`app/models/gmail_credentials.py`)

- `gmail_credentials` table: email_address (unique), access_token_encrypted,
  refresh_token_encrypted, token_expiry, scopes, is_active, timestamps.
- Tokens are encrypted with Fernet before storage; never plaintext.

## Frontend (Phase 2)

- **Settings page** — Gmail connection status, connect/disconnect buttons, OAuth
  callback handling (`?gmail=connected` or `?gmail=error`).
- **Inbox page** — "Connect Gmail account" button; when connected, keyword,
  label, from-date, and to-date filters plus a "Fetch from Gmail" button that
  calls `POST /api/gmail/process` and refreshes the email list.

## Phase 3 — Attachment processing

### Attachment service (`app/services/attachment_service/processor.py`)

- `extract_pdf_text()` — extracts text from PDF bytes using pdfplumber, with
  PyPDF2 fallback. Corrupt PDFs return empty text rather than crashing.
- `extract_docx_text()` — extracts text from DOCX bytes using python-docx,
  including paragraph and table content.
- `extract_attachment_text()` — dispatches to the correct extractor based on
  filename extension or MIME type. Supports `.pdf`, `.docx`, `.txt`; returns
  `None` for unsupported types (e.g. `.exe`, legacy `.doc`).
- `combine_email_and_attachments()` — joins email body and attachment texts
  with clear delimiters (`=== EMAIL BODY ===`, `=== ATTACHMENT: filename ===`),
  skipping attachments with no extractable text.

### Gmail attachment flow (`app/services/gmail_service/processor.py`)

`process_new_messages()` now:
1. Downloads all attachments from each Gmail message via the Gmail API
   (`users().messages().attachments().get()`).
2. Extracts text from each attachment using the attachment service.
3. Combines email body + attachment text before classification and extraction.
4. Records attachment filenames in the extraction result's `raw_extraction`
   under `attachment_files`.
5. Tracks attachment errors separately from message errors in `ProcessSummary`.

### Database

No new tables — attachment filenames are stored as metadata within
`extraction_results.raw_extraction`.

## Phase 4 — Dashboard & Analytics

### Enhanced stats endpoint (`app/api/routes/records.py`)

`GET /api/records/stats` now returns:
- Core metrics: total selected students, unique placed students, total companies,
  pending email reviews, highest package, average package
- Branch-wise statistics (grouped by Student.branch)
- Company-wise statistics (grouped by Company.name)
- Package distribution histogram (LPA ranges: 0-6, 6-10, 10-15, 15-20, 20+)

Query filters: `company`, `branch`, `status`, `date_from`, `date_to`.

Package values are parsed from CTC strings (e.g. "12 LPA" → 12.0) using regex.

### Frontend Dashboard (`frontend/src/pages/Dashboard.tsx`)

Built with Recharts:
- Six stat cards for key metrics
- Branch-wise BarChart
- Company-wise BarChart (top 10 companies)
- Package distribution PieChart with LPA range legend
- Filter bar: company, branch, status, date range, clear filters

### Database

No new tables.

## Limitations (after Phase 4)

- Student matching is by name (+ registration number when present); two
  different students with identical names are treated as one.
- Gmail credentials are stored for a single account (no multi-user auth yet).
- Legacy `.doc` files (binary Word format) are not supported — only `.docx`.
- Analytics are computed from approved records only.


