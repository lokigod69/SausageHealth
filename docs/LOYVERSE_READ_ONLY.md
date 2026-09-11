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

Official references checked 11 September 2026: [API reference](https://developer.loyverse.com/docs/), [OpenAPI document](https://developer.loyverse.com/docs/API-Reference__v1.0.yaml).
