# Vercel deployment · 9 September 2026

Live: https://ops.thesausageguy.shop . Individual owner and Moritz accounts exist. HTTPS, authenticated 6 MiB browser upload, review, private download, redeployment persistence and a real encrypted backup/restore passed. **Physical phone/camera/store-network acceptance remains open; the shared intake pilot has not been announced.**

## Where things live

| Component | Current implementation |
| --- | --- |
| Website and API | Separate Vercel project `sausage-health`, team `lokigod69s-projects`; React/Vite, FastAPI/Python 3.12 and a small Node file-signing function; functions in Singapore `sin1` |
| Accounts and records | Neon Free `sausage-health-records`, `free_v3`, `sin1`, Neon Auth off; production connection only; resource `store_nYqMD6VxPcs1iTGX` |
| Original files | Private Vercel Blob `sausage-health-originals`, `sin1`; resource `store_J4a1IsdYxssy35mI`; production prefix `pilot` |
| Source | Private GitHub `lokigod69/SausageHealth`; no records, files or credentials |
| Recovery copy | Encrypted database-and-files archive on the owner's local machine, outside Git and outside Vercel/Neon |
| AI / Loyverse | Not connected; no background specialist agents or live stock |

No paid plan was upgraded. Neon uses Free. Blob uses the team's existing Pro plan and is usage-billed. The application reserves at most **1 GiB** of uploads and allows 30 submissions per user per day; this is not a dollar spending cap. No new paid plan or monetary budget was approved. Inspect usage before raising limits or expanding the pilot.

## Deployment and DNS

Runtime source `e89483d`; deployment `dpl_8kFt6q4TwTfp7N3wdyHEuUM4XgUu`, https://sausage-health-cdi23ahn9-lokigod69s-projects.vercel.app . [CI run 34315659874](https://github.com/lokigod69/SausageHealth/actions/runs/34315659874) passed the frontend build, 46 backend tests (2 backend-specific skips), 9 Node tests, Docker build and container smoke. Later documentation-only commits do not change that runtime.

Porkbun has one new CNAME: `ops` to `9ef3c8616efcf012.vercel-dns-016.com.` (TTL 600). The three existing root/wildcard/www records were preserved. The existing public `/panglao` page still returned HTTPS 200. Vercel deployment protection remains enabled for deployment URLs; the custom domain uses the application's login. Do not disable that protection globally or merge the public site's authentication.

The production environment includes `SH_ENV=production`, exact `SH_ORIGIN=https://ops.thesausageguy.shop`, `SH_DATABASE_BACKEND=postgres`, `DATABASE_URL`, `SH_STORAGE=blob`, `BLOB_READ_WRITE_TOKEN`, `SH_STORAGE_SIGNING_KEY`, `SH_AI_ENABLED=0` and the upload reservation limit. Secrets are only in Vercel and ignored `.env.cloud` / `.data/`. Private resources are not linked to previews. Local/CI tests use isolated databases or schemas.

```powershell
vercel deploy --prod --yes --scope lokigod69s-projects
```

Build/test before future releases. Keep `requirements.txt` and `requirements.lock` as identical, fully pinned flat lists: Vercel's parser rejected `-r requirements.lock`. `.python-version` pins the actual function to Python 3.12, even if the preliminary dependency scan reports another Python version. The retained Docker path is tested separately.

## Upload and download behavior

The authenticated API allocates an intent bound to the exact user, payload, request key, immutable file IDs, declared sizes and SHA-256 values. Limits are 5 files, 50 MiB each, 100 MiB total. Intents expire after 24 hours; individual upload permissions last at most five minutes. The Node function signs only the permitted private object and operation. Browser file bytes go directly to Blob, avoiding the normal function request limit. The read-write storage token never reaches the browser.

Finalization reads the actual originals, checks sizes and hashes, and commits one record under a database lock. Retries cannot change the payload or create duplicates. A provider HTTP 400/409 may mean an immutable object already exists; it is never accepted as proof of success. Only final verification confirms the save. Downloads check account/store access and redirect using a file-specific permission lasting at most 60 seconds. The original filename remains in the record; the provider's download filename can be its opaque object ID.

The deployed CSP permits the official SDK's observed upload origin `https://vercel.com/api/blob/` and Blob hosts. An initial browser upload failed due to the old policy; a fresh document passed. The app HTML now uses `Cache-Control: no-store` and a changed document ETag to avoid retaining that policy. API responses and signing redirects are not cached.

## Accounts and private handoff

Two individual accounts were created directly in Neon: Michael (owner) and Moritz (manager, both stores). Separate generated credentials are in ignored `.data/production-login.json` and `.data/Login details.txt`. Account management remains an owner command; no email reset, signup, MFA or invitation service is claimed. For a reset, run `scripts/cloud-admin.py -m server.manage reset-password` with the command's required email argument; it prompts privately and revokes that account's sessions. Do not print secrets in a terminal log or commit them.

Moritz's initial records email was already sent in the previous session; do not resend it. No login email was sent during this deployment. Staff accounts require actual identities and store assignments.

## Recovery and maintenance

Run from this trusted admin machine with the ignored environment file:

```powershell
.venv\Scripts\python scripts/cloud-admin.py -m server.cloud_backup backup .data/backups/NEW-UNIQUE-NAME.shb --key-file .data/cloud-backup-key
```

This takes a repeatable-read Postgres snapshot, includes the immutable originals referenced by it, verifies SHA-256 and encrypts the archive with AES-256-GCM. Sessions and login attempts are excluded. The key file is necessary for recovery; preserve it in separate protected custody when arranging ongoing backups. Do not put either the archive or key in Git. The implementation buffers the archive in memory and is intended for the bounded pilot.

Restore only into a **new empty schema and a different Blob prefix**. Create the schema using a properly quoted SQL identifier, set `SH_DATABASE_SCHEMA` and `SH_BLOB_PREFIX` for the restore process, then invoke `server.cloud_backup restore ARCHIVE --key-file KEY`. The helper preserves those explicit environment overrides. The restore refuses the source schema/prefix and a nonempty target. Verify all hashes, both logins, review state and revoked sessions before any separate, explicitly planned cutover. Do not point live traffic at a test restore.

The 9 September real drill used the live Neon/Blob source, an encrypted local archive and a separate schema/private prefix. It recovered both accounts, the reviewed source and all 6,291,456 original bytes; hashes matched and restored sessions were absent. Both restored accounts could log in and read the record through the application. The isolated restore resources and exactly identified synthetic production records were removed after verification. The encrypted archive and evidence remain in ignored `.data/backups/` and `.data/restore-drill.json`. After cleanup, a separate clean empty-collection account backup was saved as `.data/backups/initial-empty-20260909.shb`.

No recurring backup, cleanup worker, monitoring or recovery cutover is installed. The technical owner remains responsible for backups: take one after the first real intake and before upgrades; agree cadence, retention, key custody and usage/failure checks before routine operation. Database-provider recovery alone does not include Blob originals.

For abandoned uploads, `server.cloud_backup cleanup-expired` removes only uncommitted intents older than their expiry plus ten minutes and refuses files referenced by a saved record. It does not delete committed originals.

## Exact remaining acceptance

On an actual phone using the store connection: log in, upload one photo and a short note, wait for the saved result, reopen/download it, and have the other account review it. Record device/network/result. Preserve a real source with provenance; label a test explicitly. Then take another complete encrypted backup and verify its manifest/hashes. Do not call browser viewport simulation a physical-phone pass or announce pilot completion before this check.

AI requires an exact provider/model, private key, monetary budget, prompt/schema run/cache versioning, proposal review and representative sample validation. Loyverse requires live read-only verification. Neither is activated by deploying this app.

Provider references: [function limits](https://vercel.com/docs/functions/limitations), [private Blob](https://vercel.com/docs/vercel-blob/private-storage), [signed URLs](https://vercel.com/docs/vercel-blob/vercel-signed-urls). These are developer references, not guides to send to the owner.
