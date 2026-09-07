# Sausage Health

A private operating workspace for **The Sausage Guy** and **Natural Mind Health**, Panglao, Philippines. First milestone: collect everyday evidence, preserve originals, and review it together.

## What works now

- Responsive observatory interface with day/night appearance, two stores, a guided introduction, collection search/filtering, and a visible roadmap.
- Server-backed notes and original file uploads: photos, PDF, spreadsheet, UTF-8 text exports, audio, and short video. Five files per update, 50 MB each, 100 MB total. Binary formats are stored for human review; they are not automatically parsed.
- Owner, manager, and staff accounts. Staff see their own submissions for their assigned stores. Managers review sources in assigned stores. The owner exports the collection index and views audit events.
- Review history, original-file hashes, request idempotency, optimistic review concurrency, and private downloads.
- Optional **OpenRouter text intake assistant**: explicitly requested drafts, quoted sources checked against input, bounded calls, cached results, no tools or automatic ledger writes. Disabled until configured. No real model call has been made during setup.
- SQLite backup with original attachments and a tested restoration into a new data directory.

## Start locally on Windows

Prerequisites: Node.js 22.21+ and Python 3.11+. In this folder:

```powershell
npm ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m server.manage local-preview
```

Run the API and frontend in separate terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8080
```

```powershell
npm run dev
```

Open <http://127.0.0.1:5180>. The generated local-only login is in `.data/preview-login.json`. This file and the database are ignored by Git. Production gets new individual accounts; do not reuse the local preview database or password.

## Validate

```powershell
npm run build
.\.venv\Scripts\python.exe -m pytest -q
```

See [validation evidence](docs/VALIDATION.md) for actual results and remaining deployment checks.

## Start here next time

1. [Current next step](protocol/NEXT_STEP.md)
2. [Current state](memory/STATE.md)
3. [Architecture and boundaries](docs/ARCHITECTURE.md)
4. [Moritz’s first week](docs/MORITZ_START_HERE.md)
5. [Deployment and access](docs/DEPLOYMENT.md)
6. [Research and source limitations](docs/RESEARCH.md)

## Scope

This is a functional **intake foundation**, not a verified financial dashboard or an autonomous retail operation. Loyverse is not connected, stock is not live, and profit is unknown. OCR, audio transcription, POS sync, financial reconciliation, customer messaging, checkout, ads, and other specialist agents are subsequent milestones. Roadmap and Agent Team screens make that distinction visible.

The existing website in `D:/CODING/SAUSAGE` and procurement app in `D:/CODING/LOYVERSE` remain independent and unchanged. Sausage Health will integrate with them through explicit interfaces after live verification.

Runtime data is single-workspace and store-scoped. It is not yet a platform for unrelated customer businesses.
