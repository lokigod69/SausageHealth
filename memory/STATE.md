# Current state · 9 September 2026

## Active cloud implementation checkpoint

The owner completed Vercel/Neon terms and asked to continue. Neon Free `sausage-health-records` is provisioned and production-connected (`store_nYqMD6VxPcs1iTGX`); private Blob `sausage-health-originals` is provisioned in Singapore and production-connected (`store_J4a1IsdYxssy35mI`). Credentials are only in ignored `.env.cloud`; generated storage signing and backup keys are in ignored `.data/cloud-private.json` / `.data/cloud-backup-key`. Production environment is set (Postgres, private Blob, AI off, exact ops origin, 1 GiB application reservation limit); no account or deployment exists yet. No paid plan was upgraded. Existing Vercel Pro Blob is usage-billed; the application quota is not a dollar spending cap.

Cloud adapters are now implemented in the working tree: Postgres compatibility with serialized critical writes, bound upload intents, no-overwrite direct private uploads through a small official-SDK signing function, server checksum verification/finalization, short-lived authorized downloads, encrypted cloud backup/restore and expired uncommitted upload cleanup. Local/container storage remains available. Verified live Blob 6 MiB upload and signed download/checksum, anonymous denial and overwrite denial; the test object was removed. Vercel reports duplicate uploads as HTTP 400/bad_request; the browser leaves success determination to full server hash/size verification. Latest local app/cloud tests: 38 passed, 2 backend-specific skips against SQLite and real Neon isolated schemas; encrypted restore and revoked restored sessions passed. Node tests: 7 passed. Build passed before the final retry adjustment; final build/CI/container and rendered cloud UI remain pending.

`ops.thesausageguy.shop` is attached to this Vercel project. DNS is not changed yet. Vercel domain configuration recommends **CNAME ops → 9ef3c8616efcf012.vercel-dns-016.com.** The refreshed Porkbun page is signed in and its DNS drawer shows exactly three existing records: root A `216.150.1.1`, wildcard CNAME `pixie.porkbun.com`, www CNAME `498659177765dc51.vercel-dns-016.com.` Preserve all three; add only ops. Next: finish source/CI/container checks, DNS, production deployment and distinct accounts; exercise live browser/phone-sized upload/review, redeployment persistence and a real encrypted off-provider backup/restore drill. A physical phone check still requires the owner; do not announce the shared pilot until it passes. Older hosting handoff paragraphs below are superseded by this checkpoint.

## Product and direction

Sausage Health is the private intake workspace for The Sausage Guy and Natural Mind Health, Panglao. Moritz supplies/reviews operations; the user owns architecture. No real business uploads or financial/stock figures have arrived. Preserve the owner's liked Tropical Observatory island and visual system. The owner rejected the invitation/password-reset notice, motivational slogans and unsolicited coaching; these are removed. Use plain functional copy and concrete next actions, not generic guide links. Help stays optional and deployment checks are owner-only.

## Verified implementation

- React/TypeScript, FastAPI, SQLite WAL and private original files; individual owner/manager/staff permissions backed by server scope.
- Intake, search/filter, review/audit, index export, backup and tested local restore. Staff see only their own submissions in assigned stores.
- Roadmap: owners, outcomes, acceptance requirements, risks/responses and an owner-only launch checklist. Next-source hints use accessible per-store records; they never certify finances or unlock phases. Labels are now Overview, Collection, Stores, Roadmap, AI tools and Help.
- Interrupted saves keep the exact pending payload/key for safe retry. Same-account reauthentication preserves the open draft. Dirty forms request an unload warning; there is no offline browser storage or crash recovery.
- Optional OpenRouter text adapter remains disabled, with no live calls. Prompt/schema version in run/cache identity, proposal review workflow and representative evaluation are explicit gates before operational activation.
- Build, 20 backend/integration tests and 6 frontend tests passed. CI built the actual non-root Docker image and passed private access, original upload, idempotency, restart persistence, review and backup creation. Real host HTTPS/phone/restore checks remain pending.
- Desktop/mobile day/night rendering and the combined API-outage/session-expiry capture recovery were exercised. Synthetic record removed; no business data in Git.

## Delivery

Private repository: https://github.com/lokigod69/SausageHealth . Source commit `87c802d`, passing CI https://github.com/lokigod69/SausageHealth/actions/runs/34305458943 (26 tests, frontend build, Docker build and container smoke). Source is published; no public application deployment or background agent service exists.

Latest Vercel setup/documentation checkpoint: `1e06ae3`, passing CI https://github.com/lokigod69/SausageHealth/actions/runs/34310277503 (all 26 tests and frontend/container build/smoke repeated successfully). Application code is unchanged; this does not verify a Vercel deployment or cloud adapters.

Local preview: http://127.0.0.1:5180 . Restart next time with `npm run start:local` on Windows; it preserves data and starts/reuses verified loopback listeners. Logs/PIDs and generated local credentials are in Git-ignored `.data/`. Never publish this directory or reuse the local preview database/password in production. Local Docker engine remains unavailable; packaging was exercised in hosted Linux CI.

Latest copy pass: desktop 1440×1000 and mobile 390×844 login, overview and roadmap inspected; no horizontal overflow. Signed out and back in, opened intake and checked store/category/form labels. Preview was restarted and opened in a fresh tab after the old tab retained a connection-error page. Original island bytes are unchanged. Screenshots: `design/evidence/plain-*`.

## Next inputs and gates

1. The owner selected **Vercel** for `ops.thesausageguy.shop`. Do not request a VPS provider/IP again. Created/linked the separate `sausage-health` project in `lokigod69s-projects` using existing CLI access. No deployment or DNS mutation occurred; local link metadata is ignored in `.vercel/`.
2. Proposed cloud storage: Neon Postgres Free (`free_v3`, Singapore `sin1`, resource `sausage-health-records`, Neon Auth off), plus private Vercel Blob. Neon setup stopped at Vercel's required terms step; the fresh browser page requires login. Waiting CLI canceled; `vercel integration list` confirms no resources connected. **Next: owner signs in/reviews the Neon Free terms at the URL in `docs/VERCEL.md`; inspect resources, resume setup, then implement/test the cloud adapters.** No paid database plan or Blob spend budget approved. Current SQLite/local files and 50 MB upload requests cannot run unchanged on Vercel. The cloud migration, direct private uploads and cloud backup/restore are not implemented.
3. Moritz's email is already in private `.data/moritz-handoff.json`; intended role manager for both stores. No hosted account exists. Follow the Vercel branch of `docs/DEPLOYMENT.md`, preserving root/www/email DNS, building/testing the cloud path and retained container, then verifying HTTPS, accounts, real phone upload/review, redeployment persistence and complete off-provider restore before claiming launch.
4. **Initial email sent and verified** through the owner's signed-in Gmail on 9 September. It requests one dated sales report per store and one supplier receipt, followed by running costs and a Loyverse export. It says online login is still being set up; it contains no credentials or localhost link. Do not resend it. Recipient, exact body and send evidence are in the private handoff file. No inbox monitoring was installed and no reply has been read.
5. Await real store records. Preserve originals and ambiguities; only supported facts enter the business baseline. The owner/Moritz handle employee training; `docs/MORITZ_START_HERE.md` is an optional reference.
6. Later: live read-only Loyverse verification; AI provider/model/budget plus activation gates. No AI agents are connected. Explain architecture in a few plain sentences: website, private records/files, then optional AI review; GitHub contains code only.

## Boundaries and resume

`D:/CODING/SAUSAGE` and `D:/CODING/LOYVERSE` remain unchanged. Their historical claims were read, not adopted as this app's evidence. Stock is not live; profitability, customer support/orders, OCR/transcription, buying, ads, legal arrangements and expansion remain unverified or planned.

Read `docs/ADVERSARIAL_REVIEW.md` for remaining risks and `docs/VALIDATION.md` for evidence. Continue only the user's requested milestone through `protocol/NEXT_STEP.md`; a backlog is not an instruction to run unattended work.
