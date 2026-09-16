# Loyverse read-only evidence

The owner supplied an access credential on 11 September 2026 and requested further intake. A manual GET-only verification and bounded import succeeded. This is **verified administrative access**, not a continuously connected website or scheduled synchronization.

## Credential and authority

The credential is in ignored `.data/loyverse-access.json`, outside Git, browser storage and the app deployment. Do not display it or copy the token screenshot into reports. Only send it as an Authorization Bearer header to `https://api.loyverse.com/v1.0`; do not follow redirects with it or put it in URLs. Personal access tokens grant broad account access according to the official reference. GET-only behavior constrains this reader; it is not proof of provider-enforced read-only token permissions.

No customer/employee profile endpoint, POS write, webhook registration, purchase, model call or schedule was used. Related repositories remain read-only. Routine replay is not installed or authorized by the mere existence of a token.

## First capture

Private batch: `.data/intake/2026-09-11-loyverse-api/`.

- `originals/`: exact response bytes from GET stores, merchant, two catalogue pages, two inventory pages and three receipt pages. The `.raw.json.txt` suffix allows the current app's TXT upload format; the contents are JSON, not converted CSV.
- `manifest.json`: method, official endpoint, query/cursor, request/response time, HTTP status, byte count and SHA-256. It contains no Authorization header. The receipt request uses a frozen UTC created-at upper bound and starts one day before the first CSV date; the precise times and store identity stay private.
- `analysis-v2.json.txt`: validated derived comparison and source-linked line data, read with explicit UTF-8 and Decimal. Do not use the unpublished v1 draft; its platform-default decoding was corrected before publication. Raw originals never changed.
- `analysis-verification.json`: independent integer-cent comparison, source hashes, matched timestamp test and ambiguity flags.
- `Loyverse API review.txt`: current findings and information requests. It explicitly supersedes commercial next-step suggestions in the first report while preserving that report.
- `cloud-ingestion.json` and saved `*-submission.json`: exact bound imports, private attachment identities and download/retry/access evidence.

Both account metadata and raw business records remain private. The verified account exposes The Sausage Guy only. The merchant endpoint supplies currency; it does not supply the configured timezone. Natural Mind Health's account/source scope remains unresolved. Do not assume this token can read the other store.

## Comparison contract

`scripts/reconcile_loyverse_api.py` is an offline comparator. It has no network client, credentials or database writes. Parse raw JSON with `json.loads(path.read_bytes(), parse_float=Decimal)`; never rely on a Windows default text encoding or binary floating-point money.

Validate source hashes, final pagination and unique identities before comparison. Join CSV store labels to verified API store IDs and match receipt numbers within that store/account. Check receipt line IDs, variant IDs and SKUs explicitly; use names for display, not primary identity. The initial matched catalogue and receipt mappings passed; evidence and exceptions belong in the private batch.

The current money mapping intentionally supports closed zero-tax receipts without tips or surcharges. Other cases, unknown signs, cancellation, duplicate identities, non-finite values and broken line/payment arithmetic must stop for a separately validated mapping. In the observed API refunds, amounts and quantities are positive magnitudes; apply the refund sign once in derived data. The CSV is already signed. This source comparison does not establish actual unit cost, profit, tax liability or settlement.

Timestamp equality at a candidate UTC+8 offset is an observed match, not a fetched timezone setting. Receipt filtering uses `created_at`; business reporting uses `receipt_date`. Delayed uploads were observed. A completed page chain is not an atomic snapshot or proof that every trading-day receipt has reached Loyverse. Preserve the capture cutoff and all original timestamps.

Do not combine the CSV total and overlapping API total. Current comparisons report overlaps, API-only and missing keys separately. Before an automatic integration, test incremental update windows, delayed arrivals, changed/cancelled receipts, replay and cross-batch deduplication. The private first-capture script has fixed scope and immutable filenames: do not rerun it over the existing originals.

Current next inputs are health-store source/access, an independent Sales summary and closing reconciliation, cost-unit documents, dated stock counts/movements and running costs. Product and commercial changes remain deferred while the owners collect and interpret evidence.

## Items page · in-app catalogue reader

A second, separate reader was added to the application on 15 September 2026: `server/loyverse.py` and the **Items** page. It is still GET-only and still not a synchronization service.

**What it does.** When someone with the owner or store-operator role presses refresh — and once a day on a schedule since 16 September — the server makes one bounded set of GET requests (`/merchant/`, `/stores`, `/categories`, `/items`, `/inventory`, `/receipts`) and stores the normalized result as one dated snapshot in `loyverse_syncs`. The page then reads that snapshot. It lists every item, variant, SKU, barcode, category, per-store price, recorded cost, stock, optimal stock, low-stock threshold and **units sold per week**, and flags what is below optimal or at the low-stock threshold.

**Sales per week.** Receipts are fetched with `created_at` but counted by `receipt_date`, because that is the business date; the fetch starts `LATE_UPLOAD_GRACE_DAYS` before the window so an upload that arrived late still lands in the week it belongs to. The window is always whole weeks (`SH_LOYVERSE_SALES_DAYS`, default 28) so a weekly average never divides by a ragged period. Refunds arrive as positive magnitudes and the sign is applied exactly once, matching `scripts/reconcile_loyverse_api.py`. Cancelled receipts, other receipt types and receipts whose business date falls outside the window are each counted separately and never folded into a total. Unlike stock, a variant with no line in a complete window genuinely sold nothing, so it reads 0 rather than unknown — but a snapshot taken before sales existed reports absence, not zero. These are counted units. No revenue, margin or profit is derived.

**The daily schedule.** `vercel.json` declares one cron at 22:00 UTC, which is 06:00 in Manila, so the completed trading day is in the numbers before the shop opens. `/api/cron/loyverse` answers 404 to anyone who does not present the exact `CRON_SECRET`, including a signed-in owner. The scheduled run skips the click cooldown, since it runs once by definition, but it is still bound by the daily cap and still writes nothing to the POS. It is attributed to a dedicated `scheduled-sync@sausage-health.invalid` account with role `staff`, no stores and a password whose plaintext was generated and discarded, so the run is auditable but the identity can never be signed in to. A schedule that only reads is not permission to write.

**What it is not.** There is no webhook, no background worker and no POS write. A stored snapshot is a dated copy of the catalogue, not a live till and not an inventory ledger. Nothing on the page derives stock value, margin or profit, and no receipt or sales figure is read by this reader.

**Authority.** The connection stays off until `SH_LOYVERSE_ENABLED=1` is set on the API server. The existence of a credential in `.data/loyverse-access.json` does not switch it on. The credential is read on the server, sent only as an `Authorization` header to `https://api.loyverse.com/v1.0`, never placed in a URL, never returned to the browser and never written to the database or an error message. Redirects are not followed.

**Bounds.** `SH_LOYVERSE_COOLDOWN_SECONDS` (default 60) and `SH_LOYVERSE_DAILY_SYNCS` (default 24) keep the account's published limit of 300 requests per 300 seconds well out of reach. One refresh at a time; an interrupted run is released after five minutes. Pagination is cursor-based and bounded at 40 pages per collection: a longer chain raises instead of publishing a snapshot with a hidden gap. A failed refresh leaves the previous snapshot in place and reports a generic message, because provider bodies can carry account data or the credential.

**Unknown is not zero.** The normalizer refuses to turn an absence into a number:

| Source condition | Reported as | Why |
| --- | --- | --- |
| `track_stock` false | *Not tracked* | Loyverse sets those inventory levels to 0; that zero is not a count. |
| Composite item without production | *Components only* | Loyverse holds the components' stock, not the item's. |
| No inventory level for a variant and store | *Unknown* | A missing level is missing, not empty. |
| `optimal_stock` / `low_stock` absent | *Not set* | Upstream default is null: no target has been chosen. |
| No store settings returned for a variant | *No store settings* | The row is marked absent rather than filled with item defaults. |
| A genuine `in_stock` of 0 | `0` | A real counted zero is preserved exactly. |

Quantities and money are parsed with `json.loads(..., parse_float=Decimal)` and carried as exact decimal strings; floats and non-finite numbers are refused. A shortfall against optimal stock is calculated only when both numbers are known. Note that Loyverse starts a variant `cost` at 0.00, so a zero cost may mean it was never entered — it is displayed, never treated as a verified unit cost.

**Store identity.** `SH_LOYVERSE_STORE_MAP` maps Loyverse store ids to `sausage` or `health`. Nothing is auto-assigned: an unmapped Loyverse store is shown to the owner as unattributed and is hidden from store operators, and a mapping entry naming a store this account does not return is reported as having no effect. This preserves the open question about Natural Mind Health's account rather than answering it by assumption.

**Access.** The item list mirrors a whole POS account rather than an individual submission, so it follows the review roles: the owner and store operators can open and refresh it; store team accounts are refused by the API, not only hidden in the interface. Store operators see only stores mapped to their assigned shops.

**Verification.** `tests/test_loyverse_catalogue.py` covers the normalization rules above, identity and duplicate refusal, role and store scoping, the cooldown and daily cap, snapshot retention, and that the credential never reaches a response. All cases are synthetic; no live business data or credential is in the repository. The live account has not been read through this new reader — that remains an owner action once the connection is switched on.

## Performance page

A second page derived from the same receipt read, added 16 September. `server/performance.py` turns the receipts into one block of trading figures per store: takings and units per calendar day, a weekday-by-hour heatmap, per-variant totals with first and last sale, basket averages and the share of takings held by the top ten products.

Everything on it is a reported observation of what the POS recorded. It is not reconciled against cash, bank or settlement, and nothing derives cost, margin or profit. The only money field used is the amount each receipt states was collected, with refunds subtracted exactly once.

Rules the aggregation keeps:

- Cancelled receipts, unknown receipt types, receipts for an unmapped store and receipts without a business date are each counted separately in `skipped` and never folded into a total.
- A calendar day with no receipts is reported as having none. That is deliberately not a claim that the shop was closed.
- Local hours use `SH_LOYVERSE_UTC_OFFSET_HOURS`, default 8. Earlier receipt reconciliation matched UTC+8, but the store's configured timezone is still unconfirmed upstream, so the figure is labelled as an assumption on the page.
- Receipts carrying tax, tip or surcharge are counted in `money_flags` and surfaced as a warning, because the money mapping this project validated covers receipts without them. The live account currently has none.
- `SH_LOYVERSE_EXCLUDED_PERIODS` marks spans that are not representative. Marked days are flagged in the data and drawn differently, never dropped silently. The owner is prompted to set one when none exists.

The page separates two things that look alike but are not: a product with stock left and a short cover, and a product that is **already** out of stock while still selling. The second is a sale that cannot happen today, not a warning about next week.

Depth is whatever the account holds. On 16 September that was 1,587 receipts across 87 trading days from 2026-06-21, with no earlier receipts to fetch.

Official references checked 11 September 2026: [API reference](https://developer.loyverse.com/docs/), [OpenAPI document](https://developer.loyverse.com/docs/API-Reference__v1.0.yaml).
