# Initial research · 8 September 2026

Sources were checked to guide this foundation. Business observations from the founder are not treated as audited facts.

## Robinsons at Bellemar

The founder reports that a Robinsons supermarket recently opened near Alona and drew large crowds. Publicly indexed posts attributed to Panglao’s municipal office describe a **September 4, 2026** opening in **Tawala, Panglao**, and identify **Bellemar** as the location. A provincial-information-office mirror also reports the opening at Bellemar Lifestyle Center. Those mirror pages support the reported date/location, but are not the original municipal website:

- [Municipality of Panglao post mirror](https://www.findglocal.com/PH/Panglao/102784958903182/The-Municipality-of-Panglao)
- [Provincial Information & Media Office post mirror](https://www.findglocal.com/PH/Tagbilaran-City/105987848851231/Provincial-Information-%26-Media-Office)

The indexed [Robinsons Supermarket company page](https://ph.linkedin.com/company/robinsons-supermarket) also surfaced a September 4 Bellemar opening announcement, but the fetched page body did not expose that exact post. The [Bohol tourism shopping page](https://tourism.bohol.gov.ph/where-to-shop/) similarly had a Panglao listing in search results that did not appear in the fetched body. Treat the opening as **corroborated by public reports, primary announcement not fully retrieved**, and recheck the original announcement or a store visit before quoting it in marketing. No claim about aisle length, revenue, customer counts, price advantage, or long-term demand was independently verified.

## Competitive response: hypotheses to test

Crowds at an opening can reflect novelty and promotions as well as durable demand. They do not establish how much demand either independent shop loses. Start collecting daily sales immediately, using historical messages to establish a before/after series. Compare the same weekdays and annotate closures, renovations, promotions, stockouts, and seasonal events.

Working hypotheses: the stores may compete through reliable specialty stock, house-made products, fast helpful communication, repeat relationships, and convenient delivery. These are experiments, not established differentiators. Verify which products Robinsons actually stocks and compare identical brands, weights, pack sizes, prices, and dates. Avoid a store-wide discount strategy before margin is understood.

Suggested first evidence: a dated 15–20-item overlap basket, shelf-availability observations, customer-request log, top-seller/slow-stock reports, and stockout frequency. Do not generalize about Filipino customers or employees. Segment actual needs: nearby residents, expats, tourists, restaurants, fitness/wellness shoppers, price-sensitive customers, and time-sensitive customers, then measure which segments appear in real transactions.

## Loyverse and current projects

[Loyverse’s official API reference](https://developer.loyverse.com/docs/) documents store/item/inventory/receipt resources and update webhooks. That supports a read-only integration architecture. It does not prove the business’s token, store mappings, SKU definitions, or stock counts are correct. No live account was queried.

The local procurement project’s saved state claims implementation and tests are substantially complete, with live Loyverse verification and real mappings still pending. Sausage Health’s implementation did not rerun those tests and did not change that repository.

The [existing Sausage Guy site](https://www.thesausageguy.shop/panglao) is a customer-facing discovery and WhatsApp conversion site. Local source review shows an explicit public/private product-data boundary. Preserve it when adding current availability. Current public content is not evidence of physical stock.

## AI and subscriptions

[OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth) distinguishes ChatGPT subscription access for developer tools from API-key usage billed through the API account. No enterprise or production runtime entitlement is inferred from a personal subscription. Separate store application accounts from coding-tool access.

[OpenRouter’s API reference](https://openrouter.ai/docs/api_reference/overview) documents its normalized chat-completions interface, model selection, JSON output options, and limits. The initial adapter targets that documented endpoint, validates returned data itself, and requires an explicitly configured model. It makes no assumption that every model supports every parameter or has suitable extraction quality. No paid call was made in setup.

[OpenAI’s structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs) explains that valid JSON alone does not ensure schema conformance. The application therefore validates the schema and verifies verbatim quotations, while retaining human review of meaning and correctness.

## Corporation, investment, and tax

[SEC eSPARC](https://esparc.sec.gov.ph/application/selection) is an official registration entry point for Philippine corporations. The founder’s incomplete description is not enough to determine the correct entity, ownership rules, investor agreement, or tax treatment. No legal structure or percentage is recommended here. Confirm the exact proposed entity and current registered business/operator with a Philippine lawyer and accountant before turning ownership, investor participation, payroll obligations, or taxes into system rules.

Capture the resulting documents privately, note the professional’s confirmed treatment and effective date, and configure the future financial model accordingly. Investor funding, purchase payments, and sales must remain distinct. This project does not draft an arrangement to circumvent ownership restrictions and does not assume a private investor side agreement is enforceable.
