# Validation · 8 September 2026

## Local checks

- `npm run build`: passed. TypeScript compilation and Vite production build. Main JS about 250 KB / 78 KB gzip; CSS about 51 KB / 11 KB gzip, excluding fonts and illustration.
- `python -m pytest -q`: **20 passed**. Two dependency deprecation warnings from Starlette/httpx/AnyIO, no test failures.
- `docker compose config --no-env-resolution`: passed configuration parsing. No environment values or credentials needed for that check.
- Docker engine: unavailable on this host. The container image and HTTPS deployment were not exercised.
- Git ignore verification: runtime database, local preview credentials, and `.env` are excluded. Business data is not included in the repository.

## Behavioral coverage

Authentication, HttpOnly/SameSite cookie attributes, origin/header enforcement, logout, persisted login rate limits, password reset with session revocation; note persistence across clients; request idempotency; staff self-only visibility; store scoping; manager review boundaries; original file names/hashes/bytes; private downloads; failed-upload cleanup; invalid input; optimistic review conflict; audit records; private export; actual backup into ZIP and restoration into a fresh directory with readable originals and login; request body size gate; AI disabled state, schema and quote validation, cache reuse, call limit reservation, role authorization, provider failure redaction, and the mocked HTTP provider contract.

Model tests use synthetic sources and a mock provider. No paid AI calls, real financial figures, POS writes, purchases, or customer messages were made.

## Browser inspection and interaction

The working app was inspected in the Codex in-app browser at desktop (1440×1000), intermediate window width, and mobile (390×844). Wide and narrow layouts were visually inspected; the hero was adjusted to contain the full island, and mobile headline sizing was reduced so the first action remains prominent. The closed mobile drawer is hidden from keyboard/assistive navigation.

Exercised: login; two-step intake with store/category selection; attaching a synthetic TXT source through the file chooser; saved confirmation; reload persistence; source detail; review note; mark reviewed; collection search and review-status filters; mobile navigation; store profiles; roadmap phase selection; agent readiness; owner activity view; and day/night appearance. Mobile collection did not overflow horizontally (document width 375 CSS px within a 390 px viewport, including scrollbar).

Synthetic browser record: `Preview check — not a business record`. Its text explicitly disclaimed business figures. It was used solely for local validation and removed after checks; evidence screenshots may show it. No real store data has been supplied.

Screenshots are in `design/evidence/`. They are evidence of local rendering and interaction, not a claim of physical Android/iPhone testing or deployed availability. AI draft rendering against a real provider, actual phone camera formats, unreliable store networks, and production TLS remain target checks.

## External checks

Private GitHub repository created as `lokigod69/SausageHealth`. Publication and CI outcome are recorded in the final protocol log after verification. Existing Loyverse/Sausage repositories were inspected read-only; their reported historical test counts were not rerun or adopted as this project’s evidence.
