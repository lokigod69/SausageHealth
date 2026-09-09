# Deployment and access runbook

**Live target: https://ops.thesausageguy.shop on Vercel.** See [VERCEL.md](VERCEL.md) for current resources, deployment commands, individual accounts and encrypted cloud backup/restore. Neon Free and private Blob are connected; the ops DNS record is set and existing customer DNS/site preserved. Do not ask for a VPS/IP, domain or Moritz email again.

HTTPS, authenticated 6 MiB browser upload, review, private download, redeployment persistence and a real separate-target encrypted restore passed. CI built/tested the retained Docker image. **Remaining: actual phone/camera/store-network upload, reopening and second-account review before announcing the shared intake pilot.** The collection contains no business records yet; synthetic tests were removed.

Private hosted login details are in ignored `.data/Login details.txt`; Moritz has a manager account for both stores. His initial records request was already sent; no login email was sent in this deployment. Do not resend the original message. Staff accounts need actual identities/assignments.

Take a complete cloud backup after the first real intake and before upgrades. No recurring backup/monitoring is installed; settle cadence, retention, separate key custody and usage checks before routine operation. Existing Pro Blob is usage-billed; the 1 GiB application quota is not a monetary cap. AI and Loyverse remain disconnected and have separate activation gates.

The remaining Docker instructions apply only to the retained local/container alternative. They are not commands for the live Neon/Blob deployment. The local Docker engine is unavailable; the actual image is built/tested in Linux CI.

## Alternative Docker deployment (not the live Vercel path)

A single HTTPS origin for the UI and API, with the app container bound to host loopback, a persistent data volume, and off-host encrypted backups. Caddy can terminate HTTPS on the host using `Caddyfile.example`. A private server network such as Tailscale can be used for technical administration while Moritz accesses the web application through an ordinary phone browser. Choosing that product does not require giving staff a developer shell or VPN workflow.

Keep this single API process for the SQLite pilot. Do not deploy it to ephemeral serverless storage. Do not point multiple services at the same database file. Keep the existing Sausage website independent.

## On a future Docker server

1. Clone the private repository using an authorized deploy credential. Install Docker/Compose and an HTTPS proxy using their official instructions for the selected OS.
2. Copy `.env.example` to `.env`, set `SH_ORIGIN` to the exact HTTPS URL **without a trailing slash**, retain `SH_ENV=production`, and retain `SH_DATA_DIR=/data` inside the container. Protect the environment file. Leave AI disabled for the first intake test.
3. Build and start:

```sh
docker compose build
docker compose up -d
```

4. Point the chosen domain at the server; configure Caddy from the reviewed example to proxy `127.0.0.1:8081`. Only the HTTPS proxy should be public. The app refuses production startup without an HTTPS origin and sets secure session cookies.
5. Create the owner and Moritz accounts. These commands prompt for a password and confirmation; replace example names/emails:

```sh
docker compose exec app python -m server.manage add-user --email owner@example.com --name Owner --role owner
docker compose exec app python -m server.manage add-user --email moritz@example.com --name Moritz --role manager
docker compose exec app python -m server.manage add-user --email staff@example.com --name Staff --role staff --stores sausage
```

Staff receive only the needed store assignment. Never copy `.data/preview-login.json` or the local test database to the production volume.

## Before real store information arrives

Verify HTTPS, cookie security, login/logout, account/store isolation, and that private API/files cannot be read while signed out. Test one photo upload and a note from Moritz’s actual phone on the store connection. Confirm file download, review, second-device visibility, and a restart preserving records. Perform a backup/restore drill on the actual server. Confirm available disk space and storage monitoring; originals can include videos.

These are pending target checks, not claimed passes. CI packaging checks passed, but the image must still be built/tested on the selected target before calling the pilot deployed.

## Backups

The implemented command snapshots SQLite through its online backup API, checks integrity, verifies each referenced attachment hash, and places the database, originals, and a manifest into one ZIP. A `.partial` file is not a completed backup. It refuses to overwrite an existing filename. Successful publication uses an exclusive same-filesystem hard link; use an ordinary local Linux/NTFS filesystem for the destination, then copy the finished archive off-host.

```sh
docker compose exec app python -m server.manage backup /data/backups/sausage-health-YYYY-MM-DD.zip
docker compose cp app:/data/backups/sausage-health-YYYY-MM-DD.zip ./
```

The ZIP contains sensitive business records, account password hashes, and sessions. Encrypt it before storing off-host, limit access, retain multiple dated copies, and schedule backups in the selected host’s normal operations system. **The app does not schedule backups automatically and ZIP encryption is not built in.** Neither GitHub source backup nor the JSON export includes a recoverable full runtime backup.

To restore: stop the application; extract a trusted backup into a **new** protected data directory; run SQLite integrity checks and verify every attachment against the `attachments.sha256` values; test login and downloads using that restored copy; revoke restored sessions; then switch the service to the validated directory/volume. Preserve the old volume until the restored application is accepted. Do not overwrite a live store database or extract an untrusted ZIP. The automated local test restores into a separate directory and checks content, checksum, integrity, and login; actual target restoration is still pending.

## Enable text intake AI only when ready

Set `SH_AI_ENABLED=1`, `SH_AI_KEY`, and `SH_AI_MODEL` on the server. The initial implementation uses the fixed official OpenRouter chat-completions endpoint. Choose a model that supports JSON mode; no model is silently substituted. Set a provider-side monetary cap and `SH_AI_DAILY_CALLS` (20 by default; UTC day). Restart the app. Secrets stay server-side.

Each extraction is an explicit manager/owner action and sends this record’s contextual fields, note, and readable UTF-8 TXT/CSV/TSV content, capped at 18,000 total characters. It does not send binary photos, PDFs, spreadsheets, audio, video, or other records. The UI explains this before the action. Long text can be truncated. No background “digest all” job exists yet.

Evaluate at least ten representative records: refunds, mixed currencies, per-kg versus per-pack pricing, duplicate days, ambiguous dates, Filipino/English notes, missing totals, and an instruction embedded in the source. Inspect every proposed fact. Test provider failure, limits, and restarts without losing originals. Quote checking is only a partial grounding check, not a guarantee of correctness.

Before activating against operational records, version prompts/schemas in the run and cache identity and define the proposal-review workflow. These are explicit remaining implementation gates from `docs/ADVERSARIAL_REVIEW.md`; current `ai_runs` records do not have those fields. Do not enable merely because the environment variables exist.

## Password reset and incident response

Accounts are administered directly by the technical owner. The initial CLI provides account creation; to reset an existing account, use the reviewed `reset-password` command. Resetting revokes that account’s sessions. There is no self-service email reset or MFA in this milestone. If a credential is exposed, revoke sessions and rotate it before reopening access.

Use the logged database schema version and tested migrations for future upgrades. `initialize()` only creates missing pilot tables; it is not a general production schema-migration system. Back up before upgrades.
