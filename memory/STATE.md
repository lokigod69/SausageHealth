# Current state · 15 September 2026

## Latest handoff

The owner requested a printable document to forward to Moritz and clarification of online login. Verified the hosted homepage and Moritz's existing login on 15 September: HTTPS works and all seven updates/sixteen attachments remain visible, none human-reviewed. Created a visually checked three-page PDF and a separate Moritz-only login TXT in ignored `.data/handoffs/2026-09-15-moritz/`. The PDF covers login/upload/review, prioritized source requests, the real-phone check and owner setup responsibilities. No passwords/API tokens are in the PDF, and no owner credentials are in the Moritz login file. The owner is to forward these; no email/message was sent and no application record or deployment changed. The exact immediate handoff is to send both files, then Moritz logs in and completes the first source/phone steps. Remaining business inputs and gates below are unchanged.

## Active milestone

**Read-only Loyverse intake and CSV/API comparison are complete. Stay in feeding and digestion: collect, check and understand.** The owner explicitly deferred placement, bundles, pricing/marketing experiments and other commercial changes. Next establish Natural Mind Health's account/source, then collect cost-unit, closing/control, stock-count/movement and running-cost evidence. Moritz's operating review remains pending.

Live workspace: https://ops.thesausageguy.shop . Michael owner and Moritz manager accounts already exist. The owner deferred personal login/phone testing while requesting intake; do not badger for login, domain, provider/IP or Moritz's email again. Preserve Tropical Observatory and plain copy. `D:/CODING/SAUSAGE` and `D:/CODING/LOYVERSE` remain unchanged/read-only.

## Items page · catalogue reader (15 September)

The owner asked for an Items tab synced with the Loyverse API. `server/loyverse.py` and the Items page now read the catalogue **on request only**: someone with the owner or store-operator role presses refresh, the server makes one bounded set of GET requests to `/merchant/`, `/stores`, `/categories`, `/items` and `/inventory`, and the normalized result is stored as one dated snapshot. No schedule, webhook, background worker, receipt/sales endpoint or POS write exists. The page lists every item, variant, SKU, barcode, category, per-store price, recorded cost, stock, optimal stock and low-stock threshold, and flags what is below optimal or at the threshold.

**The live account has not been read through this reader.** It stays off until `SH_LOYVERSE_ENABLED=1` is set on the API server; the credential in `.data/loyverse-access.json` alone does not switch it on. Switching it on, and setting `SH_LOYVERSE_STORE_MAP`, are owner actions. Until a store id is mapped, no Loyverse store is attributed to The Sausage Guy or Natural Mind Health, so the health-store question stays open rather than being answered by assuming the single returned store.

Untracked stock, composite items without production, missing inventory levels and unset optimal/low targets are each labelled distinctly and never shown as zero; a genuine counted zero is preserved. Money and quantities stay exact decimals. No stock value, margin or profit is derived, and a Loyverse cost of 0.00 is the upstream default rather than a verified unit cost. A cooldown and daily cap bound the account rate limit, a failed refresh keeps the previous snapshot, and no provider body or credential is stored or returned. All verification so far is synthetic: `tests/test_loyverse_catalogue.py`.

## Verified API intake

The owner supplied a Loyverse token and authorized intake. It is in ignored `.data/loyverse-access.json`; never display it, place it in URLs/Git or deploy it to a browser. Nine manual GET requests to official store/merchant/items/inventory/receipt endpoints succeeded; every page chain completed. Personal token permissions are broad; this GET-only use does not make it a provider-enforced read-only credential.

The account exposes The Sausage Guy only and confirms PHP/two decimal places. Every CSV receipt and SKU matches an API identity; all seven reported money columns reconcile exactly, also verified independently in integer cents. Item-level receipt lines are now collected, so do not request a duplicate itemized CSV merely to obtain those lines. API refunds are positive magnitudes, normalized once; CSV refunds are already negative. Overlapping snapshots are not additional sales.

Every matched receipt minute agrees at UTC+8, but configured timezone, CSV filters and complete trading-day coverage remain unconfirmed. API filtering uses created_at while business dates use receipt_date; delayed uploads were observed. Recorded unit costs, physical stock, tax treatment and profitability remain unverified.

Private batch `.data/intake/2026-09-11-loyverse-api/` contains raw `originals/`, request/hash `manifest.json`, validated `analysis-v2.json.txt`, `analysis-verification.json`, `Loyverse API review.txt`, `cloud-ingestion.json`, exact submission payloads, UI and backup evidence. Use explicit UTF-8 and Decimal. Do not use unpublished v1 with platform-default text decoding; it was corrected before upload, without altering raw bytes. Financial details, source IDs, SKU samples, staff/contact fields and credentials stay private.

Four API entries were saved in the live Collection: catalogue/account, stock snapshot, itemized receipts and **Loyverse API review — matched to first exports**. The original CSV batch `.data/intake/2026-09-11-loyverse/` and its three original source/review entries remain preserved. All seven entries and sixteen attachments are owner-authored with provenance, all needs_review. Both accounts' original downloads/hashes, exact retry identity and anonymous denial passed. The new review supersedes the old report's commercial next-step suggestions and resolved source questions; originals remain history.

**This is a manual administrative import. Automatic Loyverse sync and app AI remain off.** Website integration status describes that runtime, not this local verification. No customer/employee profile endpoint, POS write, webhook, new email, connector installation, model call or schedule was used.

## Recovery and validation

Latest encrypted complete archive: `.data/backups/loyverse-api-intake-20260911.shb`. Authenticated decryption, all seven entries, all sixteen original hashes and session exclusion passed. Prior archives remain preserved. This was a backup/content verification, not another live restore or an installed schedule. The separate-schema/private-prefix real restore passed on 9 September with both accounts, reviewed record, original hash and revoked sessions; restored logins were exercised. Synthetic validation data was removed then. Do not rerun old synthetic cleanup/restore scripts on real business data.

Source **0be499b** is published. [CI 34607921293](https://github.com/lokigod69/SausageHealth/actions/runs/34607921293) passed **63 backend/analyzer tests, 2 intentional backend-specific skips, 9 Node tests**, frontend build, actual Docker build and container smoke. Seventeen targeted source-analysis tests passed locally. The offline API comparator has no network/POS writes and rejects unsupported tax/tip/surcharge/cancellation, duplicate/sign/non-finite cases and broken line/payment arithmetic.

Desktop and 390×844 review/attachment UI inspected with no horizontal overflow; evidence is private. No physical-phone/camera/store-network result is claimed. No runtime/UI change or redeployment was needed. Runtime remains **e89483d**, deployment **dpl_8kFt6q4TwTfp7N3wdyHEuUM4XgUu**, at the ops alias. Earlier hosted HTTPS/private access, 6 MiB upload/review/hash, redeployment persistence and real backup/restore passed.

See `docs/VERCEL.md` for provider IDs, private accounts and commands. React/Vite + FastAPI use Neon Free records and private Vercel Blob in Singapore; tested local/container options remain. Existing Pro Blob usage is billed; the application's 1 GiB quota is not a dollar budget. No paid-plan upgrade or new budget was approved. No hidden worker is installed.

## Exact remaining actions

1. **Establish Natural Mind Health's own Loyverse account/source.** This token returns only The Sausage Guy. Preserve a separate export or verify separately authorized access; do not infer business absence from account scope.
2. Moritz reviews the new report and supplies supplier invoices, pack weights and selling units for cost samples; one daily cash/payment closing with a matching Sales summary; dated stock counts/movements; running costs by store/period. Save explanations as new evidence without changing originals or POS values.
3. The owner can use `.data/Login details.txt` or `.data/production-login.json` when ready. Actual phone/camera/store-network upload, original reopening and second-account review still gate full shared-pilot acceptance; administrative imports do not satisfy that gate.
4. Before routine use, settle backup cadence, retention, separate key custody and usage/failure checks. No recurring backup, cleanup, monitor or sync is installed. Private credentials, backup key and evidence currently depend on this machine's access controls and Git exclusion.
5. Any later sync needs its own milestone and validation of incremental windows, delayed arrivals, changed/cancelled receipts, replay/deduplication and freshness/failure visibility. AI requires provider/model/key/budget, prompt/schema identity, proposal review and representative evaluation. Commercial changes remain deferred until the owners explicitly choose that phase.

Read `docs/LOYVERSE_READ_ONLY.md`, `docs/DATA_INTAKE.md` and `docs/BUSINESS_MEASUREMENT_PLAN.md`. Only the owner changes architecture. No backlog item grants unattended authority. The initial records-request email was already sent earlier; private `.data/moritz-handoff.json` holds that history. Do not resend it or send credentials without specific authorization. Save exact next actions at meaningful checkpoints.
