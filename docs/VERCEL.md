# Vercel deployment checkpoint · 9 September 2026

The owner selected Vercel and asked to complete hosted login/uploads without having to manage server IPs. The separate `sausage-health` project has been created in `lokigod69s-projects` and linked locally. Project metadata is in ignored `.vercel/project.json`. This does not deploy the app or create a hosted account. The public Sausage website remains separate.

## Resource plan and current boundary

- Vercel: application at the confirmed `ops.thesausageguy.shop`.
- Neon Postgres: accounts, sessions, record metadata, review/audit history. CLI offers the `free_v3` Free plan, Singapore `sin1`, with separate Neon Auth disabled because the app already has authentication. Selected resource name: `sausage-health-records`.
- Private Vercel Blob: immutable original files. No public bucket and no uploads in GitHub. **Not provisioned or connected.** Blob is usage-billed under the existing Vercel plan; inspect actual allowance/spend controls before activation and obtain approval for any new paid plan or budget.
- GitHub: private source and project documentation only.
- AI: existing optional OpenRouter text adapter remains disabled. No model/key/budget has been supplied and no specialist agents are running. Vercel hosting does not automatically add intelligence.

The Neon install command stopped at Vercel's required terms-acceptance step. The fresh browser page requires Vercel login. The waiting CLI was canceled cleanly; no database creation/connection was confirmed. Do not leave an unobserved provisioning process running.

User handoff: sign into Vercel and review/accept the requested Free Neon integration terms at https://vercel.com/lokigod69s-projects/~/integrations/accept-terms/neon?source=cli . Do not accept third-party terms silently or upgrade to a paid database plan.

After acceptance, inspect resources first to avoid duplicate creation, then resume:

```powershell
vercel integration list --scope lokigod69s-projects
vercel integration add neon --name sausage-health-records --plan free_v3 -m region=sin1 -m auth=false -e production --no-env-pull --scope lokigod69s-projects
```

Pull credentials only to an ignored private environment file. Keep production resources isolated from preview deployments and local tests. Do not copy the preview SQLite database or local account password to production.

## Required implementation before deployment

The current application uses a writable SQLite database and local original files. It **cannot be deployed unchanged to Vercel Functions**. Ordinary function bodies also have a 4.5 MB limit, while the app accepts 50 MB files and 100 MB submissions. Changing `SH_DATA_DIR` to `/tmp` would lose durable data and is not a solution.

1. Add a Postgres persistence implementation and an explicit schema initialization/migration path. Preserve password/session handling, store/author authorization, throttles, review versions, audit history and request idempotency. Exercise concurrent writes against real Postgres. Retain the working local/container option until the cloud path passes equivalent tests.
2. Add authenticated, limited direct-to-private-storage uploads so file bytes do not pass through a function body. Allocate an upload intent owned by the user with fixed store/category/context, file IDs, allowed size and expiry. Never let the client choose arbitrary storage paths or read-write credentials.
3. Verify uploaded bytes and SHA-256 server-side, finalize an immutable original and transactionally link its record. Preserve the current exact-payload retry behavior. An upload to temporary storage alone is not a saved record. Handle duplicate finalization, expired sessions/tokens, partial upload failures and abandoned files.
4. Authorize every download against the owning record. Use a short-lived, file-specific private download mechanism that handles files over the function response limit. Never expose a whole-store token or make the bucket public.
5. Add the Vercel UI/API routing and environment configuration, with all business routes authenticated and AI disabled. Use the actual production origin; keep the existing customer site's root/www/email DNS intact. Do not publish a static login that calls a nonexistent API.
6. Replace the SQLite-only backup procedure for this cloud deployment with a consistent Postgres + original-files backup, encrypted off-provider copy, checksum manifest and tested restore into separate resources. A managed database backup does not automatically back up Blob files.
7. Build/test the application and retained container, deploy to the selected project, verify HTTPS and signed-out boundaries, create separate owner/Moritz accounts, and test real phone upload/review plus cloud restart/redeployment persistence. Announce shared intake only after the restore and device checks pass.

No application code or cloud adapter was changed at this checkpoint. `psycopg[binary] 3.3.5` and `vercel 0.10.0` were installed into the ignored local venv for capability inspection only; they are not in the project's dependency manifests. The inspected Python Blob SDK has private get/put but no public signed-URL helper, so do not assume TypeScript SDK examples work unchanged in Python. Choose and test the supported upload implementation before adding runtime dependencies.

## Verified provider references

- [Vercel Function limits](https://vercel.com/docs/functions/limitations): request/response size and execution constraints.
- [Vercel storage options](https://vercel.com/docs/storage) and [Postgres integrations](https://vercel.com/docs/postgres): persistent storage lives in connected services.
- [Private Blob](https://vercel.com/docs/vercel-blob/private-storage): authenticated files, separate private stores.
- [Vercel signed URLs](https://vercel.com/docs/vercel-blob/vercel-signed-urls): bounded direct upload/download permissions; use a supported SDK.

These are implementation references, not a DNS guide to send to the owner. Give the owner only the concrete next action.
