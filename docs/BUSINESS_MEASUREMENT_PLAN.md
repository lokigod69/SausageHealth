# Business measurement plan

The current phase is **feeding and digestion: collect, check and understand**. The owner explicitly deferred commercial changes on 11 September. Establish what the records mean, how complete they are and which questions remain open. Product placement, bundles, pricing tests, campaigns and purchasing changes are outside this milestone.

The Collection's **Loyverse API review — matched to first exports** updates the earlier review and its next-step suggestions. Preserve the first report as history; use the newer evidence and scope for current work.

## 1. Establish a usable baseline

The first live read-only API check confirms the account currency and maps The Sausage Guy's CSV receipts/SKUs to API identities and item lines. Exact results are private. The other store is absent from this account; establish whether it has a separate account/export. The first file's catalogue capture time, export filters and configured timezone still need confirmation. Receipt timestamps agree with UTC+8 in this matched sample, which is evidence of alignment, not a retrieved timezone setting.

Obtain a Sales summary control for the same period and a complete daily closing reconciliation. A duplicate itemized CSV is no longer needed merely to obtain the Sausage Guy lines already retrieved. Reconcile refunds once using each source's sign convention; overlapping exports/API reads are separate snapshots until deduplicated by stable account/store/receipt/line identities. Do not add their totals together.

Check a small sample of supplier/production costs against receipt pricing in matching units: piece, pack, kg and yield are distinct. Count a small set of products physically and explain stock differences through receiving, transfers, spoilage and adjustments. Preserve the initial export; record confirmed corrections as new evidence. The owner controls system changes, and Moritz confirms operating facts.

Outcome: known source coverage and a documented set of unresolved exceptions. A successful file import or arithmetic check does not certify the costs or stock.

## 2. Define the measures before adding dashboard numbers

| Measure | Decision it supports | Calculation / required evidence |
| --- | --- | --- |
| Reported daily net sales and sale receipt count | Understand recorded trading activity | Sales less discounts/refunds, by confirmed store-local date; full-day coverage and cancelled-receipt handling confirmed |
| Cash/payment reconciliation difference | Find missing deposits, recording errors or unsettled payments | Expected receipts and other movements versus counted cash/settlements; opening cash, fees, store credit, payouts and timing explicitly separated |
| Average sale receipt | Describe basket value in a defined period | Net value of Sale receipts divided by Sale receipt count; refunds reported separately; sales alone do not establish contribution |
| Product contribution | Understand product economics after cost validation | SKU-level net sales less validated matching-unit product costs and relevant variable fees; historical costs, quantities, refunds and waste required |
| Availability and stock accuracy | Explain recorded balances and count differences | Dated counts and recorded movements; explicitly log unavailable products/customer requests. A negative POS balance is a discrepancy, not a physical count |
| Waste and expiry cost | Understand where products and costs go | Dated quantities, reasons, validated unit cost and in-house production yield. Do not infer waste from a falling balance |
| Store operating result | Establish whether the store covers its costs | Validated sales/product cost plus period-matched rent, payroll, electricity, delivery, repairs and other overhead; allocations and accountant-confirmed tax treatment required |

Money remains exact decimal/minor-unit values. Missing is distinct from zero. Do not combine counts of packs, pieces and kilograms into an inventory total. Define a complete week and comparable trading days before measuring a trend. Keep source coverage visible beside each result.

## 3. Explain exceptions and review the baseline

Use the source-linked cost, stock and reconciliation samples to ask concrete operating questions. Is cost recorded per kilogram while the sale is a pack? Was a delivery or transfer recorded? Does a payment settle on another day? These are questions to resolve with documents and Moritz, not answers inferred from an unusual number.

Keep an evidence list: confirmed fact, supporting source/date, remaining ambiguity and next missing input. Record operational explanations as new submissions. Technical checks do not substitute for Moritz's review, and proposed interpretations do not update POS balances or financial ledgers.

Exit this phase only when the owners have reviewed coverage and the main unresolved questions, then explicitly choose the next milestone. Do not infer Robinsons' impact, customer preferences, profitability or expansion readiness from one short export. No commercial experiment is scheduled by this plan.

## 4. Automate only what is understood

CSV intake and a manual read-only API import work now. The screenshot's Zapier, Make and other connectors are optional app-to-app transfer services; none is required. The verified manual API read does not install a recurring integration in the website. See [LOYVERSE_READ_ONLY.md](LOYVERSE_READ_ONLY.md) for the bounded evidence and limitations.

Before any later synchronization milestone, validate incremental pagination, created-at versus receipt-date handling, cancellations/refunds, retries and cross-batch deduplication. Set freshness/failure visibility and approve any required cost. Preserve the related ProcurePilot repository as read-only until scope explicitly expands. Build no stock writes, automatic purchases, ad spend or customer commitments from this plan.

The app has no connected AI model. Future extraction needs an exact provider/model, budget and representative validation, with source-linked proposals and human review. AI should reduce repetitive work after the data contract is known.

References checked 11 September 2026: [Loyverse exports](https://help.loyverse.com/help/exporting-data-from-loyverse-account), [item/variant fields](https://help.loyverse.com/help/importing-and-exporting), [marketplace](https://loyverse.com/marketplace), [official API](https://loyverse.com/en-us/loyverse-pos-api).
