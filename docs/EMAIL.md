# Email: Resend + Hostinger mailbox backup

MixMint sends every email through `apps/core/mailer.py`:

1. **Resend** (HTTP API) while it's under its own limit (free: 100 a day, 3,000 a month).
2. **Hostinger Mail over SMTP** when Resend is missing, failing, paused or at its limit.

Bulk messages from Admin → Messages use Resend's batch API first, then the Hostinger mailbox for the rest.
Sends are counted per provider and in total; Admin → Settings → Plans and costs shows both.

## Set up the Hostinger mailbox (you, in hPanel)
1. hPanel → **Emails** → set up mail for `mixmint.site` → create a mailbox, e.g. `hello@mixmint.site`.
2. hPanel → Emails → **DNS settings / Connect domain**: let Hostinger add MX, SPF, DKIM records
   (the domain is at Hostinger, so this is one click). Keep the Resend records (`send.mixmint.site`, `resend._domainkey`).
3. Add a DMARC record if you don't have one: `_dmarc` TXT `v=DMARC1; p=none; rua=mailto:hello@mixmint.site`.

## Variables (Vercel → Settings → Environment Variables)
| Name | Value |
|---|---|
| `SMTP_USER` | `hello@mixmint.site` (the mailbox you created) |
| `SMTP_PASSWORD` | that mailbox's password |
| `SMTP_HOST` | optional, default `smtp.hostinger.com` |
| `SMTP_PORT` | optional, default `465` (SSL). `587` uses STARTTLS |
| `SMTP_DAILY_LIMIT` | `100` (free/trial mail) or `1000` (Business Starter), as shown in hPanel → Mailboxes → View limits |
| `EMAIL_PROVIDER` | `auto` (default: Resend, then Hostinger), `smtp` (Hostinger only), `resend` (Resend only) |

`FROM_EMAIL` can stay `noreply@mixmint.site`: over SMTP the message is sent as the mailbox
(Hostinger only relays mail from the logged-in address) with Reply-To set to `FROM_EMAIL`.
If Resend shuts down, set `FROM_EMAIL=MixMint <hello@mixmint.site>` and `EMAIL_PROVIDER=smtp`.

## Check it works
`python manage.py send_test_email you@gmail.com --provider smtp`

## Where SMTP works
- Vercel: yes (ports 465/587; port 25 is blocked).
- Railway Free/Trial/Hobby: **no**, outbound SMTP is blocked. Railway Pro: yes.
