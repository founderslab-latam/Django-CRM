# Hostinger VPS + Traefik

A concrete production deployment: one Hostinger KVM VPS, Docker Compose, and a
Traefik instance that is **already running on the host** for other projects (it
owns `:80`/`:443` and an ACME cert resolver). This is the setup
`docker-compose.prod.yml` at the repo root is written for.

It is one worked example, not the only way. For the general rules behind it, read
[Production deployment](production-deploy.md), [PostgreSQL and RLS](postgresql-and-rls.md)
and [Environment variables](environment-variables.md) first.

## Topology

Two hostnames, because the SvelteKit app and Django **both** serve `/api/*` and
cannot share one origin:

| Hostname | Service | Container | Port |
|---|---|---|---|
| `crm.founderslab.cloud` | SvelteKit frontend (adapter-node) | `frontend` | 3000 |
| `api-crm.founderslab.cloud` | Django API + admin (gunicorn) | `backend` | 8000 |

`db` (PostgreSQL 16) and `redis` (Celery broker) have **no** published port and
stay on the compose-internal network. `celery-worker` and `celery-beat` share the
backend image. Traefik reaches `backend` and `frontend` over the external
`n8n_default` network (the one the existing Traefik is attached to).

Rename `crm.founderslab.cloud` / `api-crm.founderslab.cloud` in **two places** if you
need different names: the `Host(...)` labels in `docker-compose.prod.yml` and the
URL variables in `.env.prod`.

## Prerequisites

- A Hostinger **KVM 2** (2 vCPU / 8 GB / NVMe) or larger. KVM 1 (4 GB) works for a
  single user but leaves no headroom for the frontend image build or WeasyPrint
  PDF rendering — add 2 GB of swap if you use it.
- Docker Engine + the Compose v2 plugin.
- The existing Traefik on the host, with:
  - a `websecure` entrypoint on `:443`,
  - a cert resolver named `mytlschallenge` (adjust the label if yours differs),
  - a global HTTP→HTTPS redirect (standard in that setup),
  - attachment to an external Docker network — this file assumes `n8n_default`.
    Confirm with `docker network ls` and `docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}'`.
- DNS: an **A record** for each hostname pointing at the VPS IPv4 (and `AAAA` if
  you serve IPv6):
  ```
  crm.founderslab.cloud.       A   <vps-ip>
  api-crm.founderslab.cloud.   A   <vps-ip>
  ```

## Deploy

```bash
# 1. Get the code (the branch you deploy from — merge i18n + RUT into it first).
sudo git clone https://github.com/founderslab-latam/Django-CRM.git /opt/founderslab-crm
cd /opt/founderslab-crm
git checkout deploy   # whichever branch carries what you want live

# 2. Configuration.
cp .env.prod.example .env.prod
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # -> SECRET_KEY
$EDITOR .env.prod        # fill every CHANGE_ME; strong POSTGRES_PASSWORD / DBPASSWORD

# 3. Data directory, outside the repo, so `git clean` can never touch it.
sudo mkdir -p /opt/crm-founderslab-data/{postgres,media,staticfiles}

# 4. Bring it up.
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
```

`entrypoint.prod.sh` runs `migrate`, `create_default_admin`, `collectstatic` and
`compilemessages` on every boot, then execs gunicorn. There is no separate
migration step — see [Upgrades](#upgrades).

## Verify

```bash
# Backend up, RLS active, tenant role is not a superuser.
curl -sf https://api-crm.founderslab.cloud/healthz/ && echo OK
docker compose -f docker-compose.prod.yml exec backend python manage.py manage_rls --status
docker compose -f docker-compose.prod.yml exec db \
  psql -U postgres -d crm_db -c "\du crm_user"   # must NOT say "Superuser"
```

Then:

1. Open `https://api-crm.founderslab.cloud/admin/` and sign in with
   `ADMIN_EMAIL` / `ADMIN_PASSWORD`. This confirms the API, DB and TLS.
2. Open `https://crm.founderslab.cloud/` and sign in with the same credentials,
   then create the **FoundersLab** organization through the onboarding.
   - If the frontend refuses a user who has no organization yet, create the
     `Org` and your `Profile` (role `ADMIN`, linked to your user and that org) in
     the Django admin first, then sign in to the frontend.
3. Change `ADMIN_PASSWORD` (rotate the account's password from inside the app or
   admin) and remove the plaintext from `.env.prod`.

## Firewall

Docker publishes ports by writing iptables rules that **bypass `ufw`**. Since
nothing in this stack publishes a host port (only Traefik does, and it already
runs), `ufw` staying at "allow 22, 80, 443" is enough — but verify no stray
`ports:` entry crept in:

```bash
docker compose -f docker-compose.prod.yml ps --format '{{.Names}}\t{{.Ports}}'
# db, redis, backend, frontend, celery-* must show NO 0.0.0.0:-> mapping
```

## Backups

Everything durable is a bind mount under `/opt/crm-founderslab-data`. A nightly
dump plus a file sync covers it:

```bash
# /etc/cron.daily/crm-backup  (chmod +x)
#!/bin/bash
set -e
cd /opt/founderslab-crm
ts=$(date +%F)
mkdir -p /opt/crm-backups
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U postgres -Fc crm_db > /opt/crm-backups/crm_db_$ts.dump
tar -C /opt/crm-founderslab-data -czf /opt/crm-backups/media_$ts.tgz media
find /opt/crm-backups -type f -mtime +14 -delete
```

Push `/opt/crm-backups` off the box (rclone to object storage, or your
HostArmada server), and enable Hostinger's VPS snapshots as a second layer.
`staticfiles/` is regenerated on every boot — no need to back it up.

Restore: `docker compose ... exec -T db pg_restore -U postgres -d crm_db --clean --if-exists < dump`.

## Upgrades

```bash
cd /opt/founderslab-crm
./deploy.sh                       # pull + build + up (backend, celery x2, frontend)
./deploy.sh backend              # or just one/some services
```

`deploy.sh` refuses to run with a dirty working tree, does `git pull --ff-only`,
rebuilds, restarts, and tails the backend log. Migrations, `collectstatic` and
`compilemessages` run inside the backend entrypoint on start, so pull + up is the
whole upgrade — no separate migration step. Take a `pg_dump` first (the backup
cron, or by hand) for anything you are not sure is backward compatible.

## Phase 2

Deferred on purpose; none of it blocks entering customers.

- **Email.** `crm/settings.py` reads the standard SMTP knobs
  (`EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` /
  `EMAIL_USE_TLS` / `EMAIL_USE_SSL`) when `EMAIL_BACKEND` is the SMTP backend.
  To turn on real delivery: set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
  plus the host vars in `.env.prod` (see `.env.prod.example`), then
  `./deploy.sh` (rebuilds `backend` + `celery-worker`, which is what sends
  mail). Google Workspace: `smtp.gmail.com:587` needs an **App Password** (2FA
  on that mailbox) and sends only as that address — for arbitrary `@founderslab.cloud`
  senders use `smtp-relay.gmail.com` (Admin console → Gmail → Routing → SMTP
  relay). Until SMTP is on, magic-link / invite / portal / CSAT mails print to
  `docker compose ... logs celery-worker`; the app login is passwordless
  (Google or magic link) — there is **no** password field, the `ADMIN_PASSWORD`
  is only for `/admin/`.
- **Uploaded-file previews.** With `ENV_TYPE=dev` and `DEBUG=False`, Django does
  not serve `/media/` (by design — it was a cross-tenant read hole). Attachments
  still download fine through the permission-checked
  `/api/(documents|attachments)/<id>/download/` endpoints, and the invoice PDF
  renderer reads the org logo straight off disk, so the only casualty is the
  logo *preview* on the settings screen. The real fix is object storage: point
  `server_settings.py`'s S3 backend at any S3-compatible endpoint (Hostinger
  Object Storage, Cloudflare R2, Backblaze B2) via `AWS_S3_ENDPOINT_URL` — which
  also means moving to `ENV_TYPE=prod` and supplying the SES + Sentry vars it
  then requires.
- **Google sign-in.** Set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` in
  `.env.prod` and on the frontend. See [Google OAuth](google-oauth.md).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Frontend pages 500 on load, API calls from SSR fail | The `frontend` container can't reach `https://api-crm.founderslab.cloud` by hairpin NAT. Add `extra_hosts: ["api-crm.founderslab.cloud:<traefik-ip-on-n8n_default>"]` to the `frontend` service, or a DNS entry the container can resolve to the host. |
| Every form submit returns `403 Cross-site POST form submissions are forbidden` | `ORIGIN` in `.env.prod` doesn't match the URL in the browser bar exactly (scheme + host). |
| Login works but no HSTS header / `request.is_secure()` false | `TRUST_PROXY_SSL_HEADER=True` missing, or Traefik isn't sending `X-Forwarded-Proto`. |
| Traefik 504 on `api-crm.founderslab.cloud`, intermittently | The `traefik.docker.network=n8n_default` label is missing or wrong; Traefik picked the internal network it can't route to. |
| `DisallowedHost` in backend logs | Add the exact `Host` header value to `ALLOWED_HOSTS` (the compose healthcheck uses `127.0.0.1`, already listed). |
| Container healthcheck for `backend` never goes healthy | `curl`/`wget` aren't in the image — the check uses `python -c urllib…`; if you changed it, keep it Python. |
