# Current state · 11 September 2026

## Active milestone

**First real file intake is complete; owner/Moritz review and missing source data are next.** Live URL: https://ops.thesausageguy.shop . The owner completed Vercel/Neon terms and asked to continue. Neon Free records and private Blob originals are connected in Singapore. Individual Michael owner and Moritz manager accounts exist. The two owner-supplied Loyverse CSVs and a separate first-review report are now saved in the live collection, attributed to the owner with Moritz provenance, all awaiting operational review. The source scope is The Sausage Guy only. The earlier synthetic validation data remains removed. Physical-phone acceptance is still pending; the owner explicitly deferred login while asking to ingest these files.

Do not ask for a provider/IP, domain or Moritz email again. Read `docs/VERCEL.md` for actual resource IDs, deployment, private credential paths, maintenance commands and limitations. No paid plan was upgraded; existing Pro Blob is usage-billed. The 1 GiB application quota is not a dollar cap. No new paid plan or spend budget was approved.

## First business intake · 11 September

Original root files were moved byte-for-byte into `.data/intake/2026-09-11-loyverse/originals/`, hashed, analyzed read-only and uploaded through the authenticated app. A separate **First export review — findings and next steps** entry includes a readable report, supported findings, limitations and targeted data requests. Both accounts can read all three entries; private original downloads match their hashes; retries reuse the same entries; anonymous file access is denied. No source is marked human-reviewed.

The private batch contains `manifest.json`, `analysis-v1.json`, `cloud-ingestion.json`, `First export review.txt`, `analysis-verification.json`, private UI evidence and `backup-verification.json`. Keep financial amounts, item details, staff fields and all raw/derived exports there or in the private runtime, never in Git. The connector screenshot is preserved under the batch's `context/` as reference only.

Source `08d0e7a` is published. [CI run 34594272159](https://github.com/lokigod69/SausageHealth/actions/runs/34594272159) passed 52 backend/analyzer tests (2 intentional backend-specific skips), 9 Node tests, frontend build, Docker build and container smoke.

The reusable analyzer is `scripts/analyze_loyverse_exports.py`; it is an admin-run script, not an automatic upload parser or connected AI. Decimal arithmetic and an independent integer-cent reconciliation passed. It preserves signed refunds, resolves shared variant fields only within Handle, keeps variable/missing prices distinct, and rejects ambiguous keys, unsupported signs/statuses and composite rows needing separate mapping. Source cost/stock exceptions remain unverified; neither net profit nor live inventory is established.

The post-intake encrypted archive `.data/backups/first-real-intake-20260911.shb` contains all three entries/originals. Authenticated decryption, manifest coverage, all original hashes and session exclusion passed. This is a verified new backup, not another live restore drill or an installed backup schedule; the separate-target drill passed on 9 September.

Read `docs/DATA_INTAKE.md` and `docs/BUSINESS_MEASUREMENT_PLAN.md`. No connector was installed, message sent, AI called, POS changed or new deployment performed this intake. The original art and related repositories remain unchanged. Next request: confirm currency/timezone/export filters/snapshot time; obtain Natural Mind Health exports, Receipts by item plus Sales summary controls, a daily closing reconciliation and selected supplier/cost/count evidence. An optional confirmation question was asked but no answer was received; retain the uncertainties.

## Verified delivery

- Private source: https://github.com/lokigod69/SausageHealth . Runtime `e89483d`, Vercel deployment `dpl_8kFt6q4TwTfp7N3wdyHEuUM4XgUu`, current ops alias. [CI 34315659874](https://github.com/lokigod69/SausageHealth/actions/runs/34315659874) passed: 46 backend tests, 2 backend-specific skips, 9 Node tests, frontend build, actual Docker build and container smoke. Documentation-only commits can be newer than the deployed runtime.
- Live valid HTTPS, separate logins, anonymous API/file denial, manager export denial, browser 6 MiB original upload, server SHA/size verification, review and private download passed. Same record, review and exact bytes survived a new production deployment. Existing customer `/panglao` page remains HTTPS 200; only the ops CNAME was added.
- Real off-provider encrypted backup/restore passed using live Neon and Blob and a separate schema/prefix: both accounts, reviewed record, exact original hash and revoked restored sessions. Restored accounts were exercised through the app on the admin machine. Private evidence/archive retained; temporary cloud test data removed.
- Desktop and phone-sized browser UI inspected, no horizontal overflow. **No physical phone/camera/store-network result exists yet.** Initial stale-CSP upload failure was fixed, followed by a successful fresh-document upload; root HTML now has no-store caching and a fresh ETag. Python 3.12 is pinned; flat requirements.txt/lock must stay synchronized for Vercel.

## Product and architecture

Preserve Tropical Observatory's original island and plain functional copy. No invitation notices, motivational slogans, generic guides or employee coaching. Moritz supplies/reviews operations; the user alone owns architecture; staff are scoped to their own submissions in assigned stores.

React/Vite + FastAPI now support Postgres and bounded direct private Blob uploads on Vercel; SQLite/local files remain a tested local/container option. Records, originals, provenance, review/audit, exact-payload retries and export are implemented. Originals and runtime secrets never enter Git. Failed saves keep the exact draft while its page remains open; reload/OS termination can lose unsaved drafts. No offline queue.

No AI agents or live Loyverse connection exist. Optional bounded OpenRouter text extraction is disabled. No financial figures, profit, live inventory, OCR/transcription, purchasing, orders or customer automation is claimed. `D:/CODING/SAUSAGE` and `D:/CODING/LOYVERSE` remain unchanged/read-only.

## Private handoff and remaining actions

1. Owner can use `.data/Login details.txt` (also `.data/production-login.json`) for the two separate hosted accounts. Moritz's first-records request was already sent and verified earlier; `.data/moritz-handoff.json` contains that private history. No login email was sent this turn; do not resend the initial email.
2. **Next: review the first export report in Collection and resolve its source questions.** The owner will log in later. The actual phone/camera/store-network test remains a separate pending launch check; do not claim this administrative CSV import completed it.
3. The first-real-intake encrypted backup and contents checks passed. A real restore drill passed earlier, but no recurring backup/cleanup/monitoring is installed. Before routine operation, the technical owner must settle cadence, retention, separate key custody and usage/failure checks. Backup/key/evidence are currently protected only by this machine's access and excluded from Git.
4. Obtain the missing health-store exports and SKU-level receipts/control totals, then supplier invoices, costs and counts. Do not total overlapping exports as additional sales. Review ambiguities; update supported facts only.
5. Later milestones require live read-only Loyverse/store/SKU verification and AI provider/model/key/budget, prompt/schema identity, proposal review and sample evaluation. General autopilot does not authorize spending or customer actions.

Local preview can be restarted with `npm run start:local`; cloud use no longer depends on it. No hidden automation or autonomous backlog worker is installed. Save exact next actions through `protocol/NEXT_STEP.md` at meaningful checkpoints.
