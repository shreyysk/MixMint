# MixMint vault worker

Telegram keeps the permanent copy of every upload. Cloudflare R2 is only a holding area that
buyers download from.

```
DJ browser ──PUT──▶ R2 ──worker──▶ private channel  (tracks → "singles", album ZIPs → "zips")
                    ▲                     │
                    └──worker (on demand)─┘   when a buyer wants a file that already left R2
Buyer ◀── temporary R2 link (always)
```

**How long a file stays in R2.** You can change these on Admin → Support → File vault.

| Sale type | Kept in R2 |
|---|---|
| Normal release | 10 days after upload |
| Limited drop | until it sells out (at least 10 days) |
| Fetched back for a buyer | 3 more days after the last request |

**When a file is deleted from R2.** It is deleted only when all of these are true:

* its Telegram copy is confirmed;
* the Telegram copy can be fetched back;
* the file hasn't changed since it was archived.

## Why a worker

The public Bot API can send only 50 MB per file and fetch only 20 MB.

This folder runs Telegram's **Local Bot API Server** in `--local` mode:

* files up to 2 GB can be sent;
* downloads have no size limit;
* files move by local path.

The server can't run on Vercel, so it runs on a small VPS next to a small worker.

Reusing a `file_id` lets a bot *re-send* a big file without uploading it again. It does not let the bot *download* it, so it can't help put a file back into R2. The local server can.

## What you need

1. A small Linux server with a public IP.
   * It needs at least 1 GB RAM and 20 GB of disk. Files pass through the disk during a copy.
   * Examples: Oracle Cloud Always Free (ARM), Hetzner CX22, or a ₹400–500/month DigitalOcean or Lightsail box.
2. A subdomain pointing at it, e.g. `vault.mixmint.site`: add an A record in your DNS.
3. `api_id` and `api_hash` from https://my.telegram.org → *API development tools*. Any app name works.

## Install (about 10 minutes)

`vault_worker/.env` on your PC is already filled in: bot token, R2 keys, a fresh worker secret and the domain. Add `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`, then:

```powershell
# on your PC (PowerShell) — copy the folder to the server
scp -i <your-key> -r D:\mixmint2.0\vault_worker ubuntu@<server-ip>:~/
ssh -i <your-key> ubuntu@<server-ip>
```
```bash
# on the server
cd ~/vault_worker && bash setup.sh
```

`setup.sh` does the rest:

1. Checks DNS.
2. Installs Docker.
3. Adds swap on small servers.
4. Opens ports 80 and 443.
5. Moves the bot off Telegram's cloud. It asks for YES first and only does this once.
6. Starts everything and prints the three Vercel values.

## Connect MixMint (Vercel → Settings → Environment Variables)

| Name | Value |
|---|---|
| `VAULT_WORKER_URL` | `https://vault.mixmint.site` |
| `VAULT_WORKER_SECRET` | the same secret as in `.env` |
| `TELEGRAM_API_BASE` | `https://vault.mixmint.site` (the help desk bot uses your server too) |

Then redeploy, and in Admin → Support:

1. Click **Reconnect** to register the webhook on your own server.
2. Link the two private channels. Add the bot as an admin in each, then post the `/link singles …` / `/link zips …` line shown there.
3. Click **Run vault now** to copy existing uploads. The daily cleanup cron also does this, and frees R2.

## Health check

```bash
curl -H "Authorization: Bearer <VAULT_WORKER_SECRET>" https://vault.mixmint.site/health
# {"bot": true, "r2": true, "queued": 0}
```

## Security notes

* `vault.mixmint.site` is not a website. Caddy answers 404 to everything except `/jobs`, `/health` and `/bot…`, and the Bot API server itself is never published.
* You see the vault's health in Admin → Support. Nothing is shown on the vault address itself.
* `/jobs` and `/health` need the worker secret.
* The `/bot<token>/…` proxy passes only a short list of methods. It refuses local file paths, so a leaked bot token can't be used to read files from the server.
* Keep both channels **private**. Don't delete their posts: once a file has left R2, the channel post is the only copy.
