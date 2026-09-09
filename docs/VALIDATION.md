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

Private GitHub repository published as `lokigod69/SausageHealth`, foundation source commit `8747ab2`. [GitHub Actions run 34166745139](https://github.com/lokigod69/SausageHealth/actions/runs/34166745139) completed successfully: production frontend build and all 20 backend/integration tests on the hosted Linux runner. This does not validate the unbuilt Docker image or a deployed HTTPS environment.

After the development server restarted during formatting, a stale preview tab showed a connection error. A fresh tab successfully loaded the running local app and reused the session; final day/dark screenshots show the empty collection after synthetic-record cleanup. The working preview is left open for the owner.

Existing Loyverse/Sausage repositories were inspected read-only; their reported historical test counts were not rerun or adopted as this project’s evidence.

## 9 September 2026 · roadmap and intake resilience

- Local production frontend build passed; local backend suite again passed **20 tests** with the same two dependency warnings. New `npm test` passed **6 tests** for per-store starters, staff self-only suggestions, uncertain network/truncated responses and structured expired-session errors.
- [GitHub Actions run 34297518065](https://github.com/lokigod69/SausageHealth/actions/runs/34297518065), source commit `bd678e4`, passed the build, all 26 tests, the **actual Docker image build** and `tests/container_smoke.py`. This supersedes the initial unbuilt-image limitation; the local Docker engine remains unavailable.
- The container smoke uses its own disposable container and volume, synthetic account and original file. It checks non-root UID, bundled UI, production CSP/Secure/HttpOnly/SameSite headers, signed-out boundaries, origin rejection, original-file hash, repeated-request idempotency, restart persistence, private download, review and a valid backup archive. It does not test a real HTTPS proxy or restore on the selected production server.
- The first new CI smoke failed because Docker changed the ephemeral host port on restart; the test now re-reads that port. The subsequent complete runs passed. This was a test-address assumption, not a production deployment or business-data failure.
- Browser checks at **1440×1000** and **390×844**: four roadmap phase selections, day/night layout, mobile navigation, store filter, next-action store/category preselection, launch-checklist expansion and saved collection rendering. Mobile document width was 375 CSS px within the 390 px viewport, with no horizontal overflow.
- Browser resilience check: prepared one clearly synthetic note, stopped only the verified local API process, attempted save, observed uncertain-save text and locked fields, restarted with the new helper, expired only the local preview account's sessions, retried, signed in again in the same form and saved. The original note was unchanged and the database contained exactly one matching record. The synthetic record was then removed; no real business records were supplied.
- `npm run start:local` passed a fresh start, repeated invocation without duplicate servers, and restart of the missing API while reusing the web process. It guards against unrelated port owners and handles Windows venv parent/child processes.
- New screenshots: `design/evidence/roadmap-desktop.png`, `roadmap-mobile-day.png`, `overview-refined.png` and `overview-mobile-next.png`. The final phone check also caught a cramped coverage card; it now stacks in one column with readable copy and no overlapping decoration. Desktop/mobile rendering and recovery interaction were inspected; physical phone/camera/network acceptance remains pending.

The dirty-form unload warning is implemented but is not an offline-save guarantee or a validated OS-crash recovery path. Remaining gates are listed in `ADVERSARIAL_REVIEW.md` and the deployment runbook. No DNS changes, public deployment, paid model calls or live POS/customer actions occurred.

## 9 September 2026 · plain-copy correction

- Source `87c802d`: [CI run 34305458943](https://github.com/lokigod69/SausageHealth/actions/runs/34305458943) passed all 26 tests, frontend production build, Docker build and container smoke. Local frontend build and six frontend tests also passed. No backend behavior was changed.
- Inspected login, overview and roadmap at 1440×1000 and 390×844. Login uses only functional sign-in copy; no invitation/password-reset notice or motivational slogans. Mobile document width matched its available viewport width, with no horizontal overflow. Day/night views retain the original artwork.
- Successfully signed out/in using the private preview account; opened the roadmap's suggested source and checked the store/category and detail form. The deleted walkthrough's grid now uses one column; Continue remains right-aligned. The technical checklist is conditional on owner role; existing server permissions are unchanged.
- Saved six `design/evidence/plain-*` screenshots with an empty collection. No actual business upload or physical phone test occurred in this copy pass. The preview server was restarted and a fresh app tab recovered from the old tab's retained connection-error page.
- One explicitly authorized operational email to Moritz was sent via the owner's Gmail and verified by its "Message sent" response. Its private handoff file is ignored by Git. This does not validate email delivery to the recipient, a hosted login or a production deployment.

## 9 September 2026 · deployed cloud intake and recovery

- Runtime source `e89483d`, [CI run 34315659874](https://github.com/lokigod69/SausageHealth/actions/runs/34315659874): 46 backend tests passed, 2 intentional backend-specific skips; 9 Node tests passed; frontend build, actual Docker build and container smoke passed. Tests cover SQLite and isolated real Postgres schemas, grants, reservation bounds, owner/store roles, concurrent finalization/review, mismatch rejection, retry identity and encrypted restore. No provider credentials enter CI.
- Deployment `dpl_8kFt6q4TwTfp7N3wdyHEuUM4XgUu` is READY and aliased to https://ops.thesausageguy.shop. Actual Python function is 3.12. Valid HTTPS, health 200, anonymous records/files 401, separate owner/manager logins, owner export 200 and manager export 403 passed. Existing public `/panglao` still returned HTTPS 200 after adding only the ops CNAME.
- Live browser file chooser uploaded a clearly synthetic **6,291,456-byte** TXT original, exceeding the normal function body limit. Finalized record and review were visible; authenticated downloads by both accounts matched SHA-256 `74d1b8ca79e4820dfc6ef0282f7fe488c32159004a55c45ca6d988a245aea1e6`. The same record/version/hash survived deployment of e89483d. AI stayed not_connected.
- An initial browser upload failed because the page's CSP blocked the SDK upload endpoint. The endpoint was added to CSP; a fresh document upload passed. Stale-policy caching was addressed with no-store HTML and a new document ETag. Vercel rejected requirements.txt's `-r` include during one build; the failed deployment never replaced production. Both dependency lists are now flat and pinned. Provider no-overwrite rejection is HTTP400; tests require actual server hash verification before interpreting a retry as saved.
- A separate live Blob smoke also passed upload, signed download/hash, anonymous denial and overwrite denial; its own object was removed.
- **Real recovery drill:** repeatable-read live Neon snapshot plus private Blob original, AES-256-GCM archive written outside the provider to the owner's local disk, restored into a new schema/private prefix. Recovered two accounts, one reviewed record and exact 6 MiB original; sessions restored: 0. Both restored users logged in and read review state via the application on the admin machine. Archive hash: `457a64e70adb9bb8a80ab4e95f053ee350e9a7da9b0cf017badcebac2c4cb79b`. Compressed encrypted size 20,111 bytes reflects repetitive synthetic text, not lost original bytes.
- Temporary production entry, two abandoned upload intents and exact test blobs were removed after successful checks; isolated restore schema/blob also removed. Audit retains validation history. No business records arrived. Private evidence and encrypted archive/key remain ignored in `.data/`; none were committed.
- Desktop and 390×844 phone-sized UI inspected; no horizontal overflow. Private screenshot `.data/cloud-phone-review.png`. Browser simulation is **not** a physical phone, camera-format or store-network test. That acceptance remains open, as do recurring backup/retention/key custody/usage arrangements before routine operation. No recurring worker or monitoring is installed. No login email was sent this deployment.
