# Business measurement plan

Start with decisions the owners need to make: which products earn their shelf space, where cash or stock is being lost, and whether each store covers its costs. Collect the inputs for those decisions before adding more dashboard numbers. Current private findings and the specific cost/stock samples are in the collection's **First export review — findings and next steps**.

## 1. Establish a usable baseline

Moritz confirms export currency, timezone, hours/cashier filters, store scope and catalogue snapshot time. Obtain each store separately. Request receipts by item and a sales-summary control for the same date range, then a complete daily closing reconciliation. Reconcile signed refunds once; overlapping exports are separate snapshots until deduplicated by stable receipt/line identities.

Check a small sample of supplier/production costs against receipt pricing in matching units: piece, pack, kg and yield are distinct. Count a small set of products physically and explain stock differences through receiving, transfers, spoilage and adjustments. Preserve the initial export; record confirmed corrections as new evidence. The owner controls system changes, and Moritz confirms operating facts.

Outcome: known source coverage and a documented set of unresolved exceptions. A successful file import or arithmetic check does not certify the costs or stock.

## 2. Measure operations

| Measure | Decision it supports | Calculation / required evidence |
| --- | --- | --- |
| Reported daily net sales and sale receipt count | Staff timing and comparison of trading days | Sales less discounts/refunds, by confirmed store-local date; full-day coverage and cancelled-receipt handling confirmed |
| Cash/payment reconciliation difference | Find missing deposits, recording errors or unsettled payments | Expected receipts and other movements versus counted cash/settlements; opening cash, fees, store credit, payouts and timing explicitly separated |
| Average sale receipt | Test whether a bundle changes basket value | Net value of Sale receipts divided by Sale receipt count; refunds reported separately; pair with contribution, not sales alone |
| Product contribution | Decide which products/prices to retain or test | SKU-level net sales less validated matching-unit product costs and relevant variable fees; historical costs, quantities, refunds and waste required |
| Availability and stock accuracy | Prevent avoidable missed sales and investigate errors | Dated counts and recorded movements; explicitly log unavailable products/customer requests. A negative POS balance is a discrepancy, not a physical count |
| Waste and expiry cost | Improve purchasing and rotation | Dated quantities, reasons, validated unit cost and in-house production yield. Do not infer waste from a falling balance |
| Store operating result | Decide whether the store covers its costs | Validated sales/product cost plus period-matched rent, payroll, electricity, delivery, repairs and other overhead; allocations and accountant-confirmed tax treatment required |

Money remains exact decimal/minor-unit values. Missing is distinct from zero. Do not combine counts of packs, pieces and kilograms into an inventory total. Define a complete week and comparable trading days before measuring a trend. Keep source coverage visible beside each result.

## 3. Test a business change

After the relevant baseline is usable, choose one small experiment with Moritz: product placement, clearer pack/price information, a bundle, or an availability improvement. These are hypotheses; the first exports do not establish which will work.

Record the products, dates, owner, effort/cost limit, expected benefit and stopping condition before starting. Compare with an appropriate prior period or untreated product group while noting seasonality, store hours, stockouts and other changes. Use additional contribution after discounts, waste and campaign costs as the main commercial outcome. A sales increase alone does not prove the change caused it. Purchases and paid marketing need specific authority before execution.

Do not infer Robinsons' impact, customer preferences or expansion readiness from one short export. Ask about unmet requests and compare actual product-level evidence first. Convenience, specialist range and dependable availability are possible differentiators to test.

## 4. Automate only what is understood

CSV intake works now. The screenshot's Zapier, Make and other connectors are app-to-app transfer services; none is required for the current task. Later compare a direct read-only Loyverse connection with a connector against the actual recurring workflow, permissions, freshness, failure visibility and approved cost. A marketplace listing is not proof that the store has granted access or that an integration works.

Require live read-only store/SKU/receipt verification and overlap/deduplication tests before scheduling synchronization. Preserve the related ProcurePilot repository as read-only until scope explicitly expands. Build no stock writes, automatic purchases, ad spend or customer commitments from this plan.

The app has no connected AI model. Future extraction needs an exact provider/model, budget and representative validation, with source-linked proposals and human review. AI should reduce repetitive work after the data contract is known.

References checked 11 September 2026: [Loyverse exports](https://help.loyverse.com/help/exporting-data-from-loyverse-account), [item/variant fields](https://help.loyverse.com/help/importing-and-exporting), [marketplace](https://loyverse.com/marketplace), [official API](https://loyverse.com/en-us/loyverse-pos-api).
