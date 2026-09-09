# Agent departments and staged authority

The system coordinates work through durable database records and versioned policies. A person can always see what was used, what was proposed, and what still needs a decision.

| Department | Inputs | Output | Authority now | Gate before activation |
| --- | --- | --- | --- | --- |
| Coordinator | Reviewed sources, current plan, unresolved questions | Daily/weekly brief, assigned next actions | Planned | Shared operational priorities and persistent task workflow |
| Intake | Notes and text exports | Draft facts, source quotes, missing information | Built; off until model configured | Real sample evaluation, API key, exact model, provider budget |
| Finance | Reconciled receipts, costs, inventory movements, accountant rules | Source-linked margin and cash-flow explanations | Planned | Deterministic ledger, reconciliation, accountant review |
| Stock/procurement | Fresh POS stock, unit mappings, suppliers, lead times, expiry | Reorder proposals, slow-stock flags, comparison drafts | Planned; existing ProcurePilot is a candidate | Live verification of existing app and ten real SKU mappings |
| Customer host | Approved public catalog, fresh availability, delivery rules | Answers and order requests | Planned | Channel authorization, privacy boundary, reservation workflow, escalation |
| Growth | Product economics, measured experiments, public competitor facts | Campaign drafts and product hypotheses | Planned | Human budget approval and a way to measure outcomes |

## Shared contract

The target contract for each department is an actor, store scope, input version/hash, prompt/schema version, selected provider/model, status, output artifact, and a human-review state. The current text adapter has actor/source digest/model/status/output; prompts are tracked in Git but a separate prompt version in run/cache identity and a proposal approval state are **not implemented**. Complete those and the sample evaluation before operational activation. A completed model response is not a completed store action. Future background jobs need idempotency, bounded retries, lease expiry, an outbox, and owner-visible failures before they can execute externally.

Uploaded content and customer messages cannot grant tools or authority. Facts are retrieved through permission-filtered application services. Models should not receive unrestricted database, filesystem, purchase, bank, deployment, or developer-shell access.

For customer service, stale stock must lead to “let me check with the store,” not a confident inventory claim. Payment or delivery is not confirmed until the operational system has a real reservation/order event. Questions about supplements must stay within approved product information and avoid diagnosis/treatment claims.

For marketplaces, reuse the existing procurement project’s approved quote and official-app handoff pattern. Unattended checkout is not a requirement of this first release, and no checkout integration is active.

## Model and orchestration choice

Do not decide between Hermes, OpenClaw (the spoken “OpenCL” may mean this; unconfirmed), Claude Code, Codex, or a provider based on names alone. The first runtime integration is a small OpenRouter-compatible intake adapter, because provider/model selection can change without replacing the evidence system. Evaluate shortlisted models using actual English/Cebuano/Tagalog business examples and receipt formats. Record errors, quote fidelity, ambiguity handling, latency, and cost. No particular cheap model is assumed suitable before testing.

Coding subscriptions are developer tools. Production API credentials, usage budgets, and data handling are separate operational decisions. OpenAI documents subscription sign-in and usage-based API-key access as separate methods: https://learn.chatgpt.com/docs/auth . No assumption is made that a personal subscription grants enterprise access, shared-account rights, or a free production API. Give Moritz and staff application accounts; do not share a developer owner login with them.
