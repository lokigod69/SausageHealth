# Current state · 9 September 2026

## Product and direction

Sausage Health is the private intake workspace for The Sausage Guy and Natural Mind Health, Panglao. Moritz supplies/reviews operations; the user owns architecture. No real business uploads or financial/stock figures have arrived. The owner explicitly liked the island and asked to preserve Tropical Observatory; the original art is unchanged. The final refined UI awaits owner feedback.

## Verified implementation

- React/TypeScript, FastAPI, SQLite WAL and private original files; individual owner/manager/staff permissions backed by server scope.
- Intake, search/filter, review/audit, index export, backup and tested local restore. Staff see only their own submissions in assigned stores.
- Refined field-guide roadmap: owners, outcomes, acceptance requirements, risks/responses, launch checklist and Moritz quick guide. Next-source hints use accessible per-store records; they never certify finances or unlock phases.
- Interrupted saves keep the exact pending payload/key for safe retry. Same-account reauthentication preserves the open draft. Dirty forms request an unload warning; there is no offline browser storage or crash recovery.
- Optional OpenRouter text adapter remains disabled, with no live calls. Prompt/schema version in run/cache identity, proposal review workflow and representative evaluation are explicit gates before operational activation.
- Build, 20 backend/integration tests and 6 frontend tests passed. CI built the actual non-root Docker image and passed private access, original upload, idempotency, restart persistence, review and backup creation. Real host HTTPS/phone/restore checks remain pending.
- Desktop/mobile day/night rendering and the combined API-outage/session-expiry capture recovery were exercised. Synthetic record removed; no business data in Git.

## Delivery

Private repository: https://github.com/lokigod69/SausageHealth . Source commit `68b633f`, passing CI https://github.com/lokigod69/SausageHealth/actions/runs/34297084565 . Source is published; no public application deployment or background agent service exists.

Local preview: http://127.0.0.1:5180 . Restart next time with `npm run start:local` on Windows; it preserves data and starts/reuses verified loopback listeners. Logs/PIDs and generated local credentials are in Git-ignored `.data/`. Never publish this directory or reuse the local preview database/password in production. Local Docker engine remains unavailable; packaging was exercised in hosted Linux CI.

## Next inputs and gates

1. Confirm the proposed `ops.thesausageguy.shop` hostname and choose a hosting target. No new domain registration is needed for a subdomain. Read-only DNS on 9 September points to Porkbun nameservers and a Vercel target for `www`; no account access or DNS changes were made.
2. Hosting/DNS access through a private credential mechanism, Moritz account email and staff assignments. Follow `docs/DEPLOYMENT.md`, including actual HTTPS, phone and off-host backup/restore acceptance before claiming shared launch.
3. First dated sales report from each store, then receipts, operating costs, stock exports and a store tour. Preserve originals and ambiguity; `docs/MORITZ_START_HERE.md` explains the routine.
4. Later: read-only Loyverse token/store mappings and verification; AI provider/model/budget plus the review's activation gates.

## Boundaries and resume

`D:/CODING/SAUSAGE` and `D:/CODING/LOYVERSE` remain unchanged. Their historical claims were read, not adopted as this app's evidence. Stock is not live; profitability, customer support/orders, OCR/transcription, buying, ads, legal arrangements and expansion remain unverified or planned.

Read `docs/ADVERSARIAL_REVIEW.md` for remaining risks and `docs/VALIDATION.md` for evidence. Continue only the user's requested milestone through `protocol/NEXT_STEP.md`; a backlog is not an instruction to run unattended work.
