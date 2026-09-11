# Private file intake

The first batch is in ignored `.data/intake/2026-09-11-loyverse/`. Its two CSV originals were moved from the project root without changing their bytes, with SHA-256 verification. They and a separate first-review report are also saved through the live app's authenticated collection. Original receipt cashier fields stay private; the derived report does not repeat them.

## Storage and provenance

- `originals/`: untouched incoming files. Never clean or save an edited version over them.
- `manifest.json`: receipt provenance, filenames, byte counts, hashes, schema and source-record counts. File receipt time is not automatically an export timestamp.
- `analysis-v1.json`: private derived data with source hashes and CSV record references. Shared item fields resolve only within the same Handle. Prices, costs, stock and SKUs never inherit.
- `First export review.txt`: readable findings, limitations, review samples and proposed next actions; attached separately in the private collection.
- `cloud-ingestion.json`: private entry/attachment IDs, matching hashes, retry and account-visibility evidence.
- `backup-verification.json`: encrypted off-provider backup and authenticated archive/original hash checks.

No business export, customer/staff detail, report, credential or private screenshot belongs in Git. `.data/` is ignored; root CSV files are also ignored as a guard against future accidental commits. Git holds only the generic analyzer, synthetic tests, process and project continuity.

## Analysis

`scripts/analyze_loyverse_exports.py` is an admin-run, read-only analyzer. It does not upload files, call AI or write to Loyverse. Incoming uploads are not automatically parsed by the web app. Run analysis using the bundled Python runtime when following the spreadsheet workflow:

```text
python scripts/analyze_loyverse_exports.py --items PRIVATE_ITEMS.csv --receipts PRIVATE_RECEIPTS.csv --output .data/intake/NEW_BATCH/analysis-v1.json
```

It requires known headers, unique SKU and store/POS/receipt keys, finite numeric values, supported receipt signs/statuses and resolvable shared variant fields. Composite-component rows or conflicting shared fields require explicit mapping. Variable prices remain variable. Missing stock/cost values remain missing. Refund amounts retain their negative source signs; no second subtraction. Equations are checked separately from sums. Receipt descriptions are not a substitute for SKU-level sale lines.

Analysis output identifies unconfirmed currency, timezone and filters. A catalogue is an undated snapshot unless an export time is supplied. Boundary dates are not certified complete days; a date with no rows is not assigned zero sales. Cross-batch receipt deduplication, generalized composite parsing and a ledger are not implemented. Do not aggregate overlapping batch summaries.

## Publish and review

Use the existing authenticated upload-intent/finalize API or web intake. An administrative import is attributed to the owner with the actual supplier named in provenance; do not impersonate the supplier. Use one source entry per export and a separate derived review. Keep exact retry payloads/keys private, compare downloaded hashes, verify manager visibility and anonymous denial. Imported sources remain `needs_review` until an authorized operator actually reviews them. Technical parsing does not set a human review flag.

When a fact is corrected, preserve the first source and add the correction with its source/date. Never overwrite originals, silently fill costs with zero or post financial/stock adjustments from an analysis. The next requested business measurements are in [BUSINESS_MEASUREMENT_PLAN.md](BUSINESS_MEASUREMENT_PLAN.md).

After a real batch, run the encrypted cloud backup from [VERCEL.md](VERCEL.md), verify authenticated decryption, entry coverage and every original's hash. A backup of code or an index-only export cannot restore originals. Recurring backup cadence, retention, key custody and monitoring remain separate operational work; none is installed automatically by running an import.
