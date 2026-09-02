# Deploying the Archethos API

Target: **Ubuntu 24.04**, native PostgreSQL, gunicorn under systemd, nginx with
Let's Encrypt, serving **api.archethos.com**.

Ubuntu 24.04 ships Python 3.12, which is what Django 6.1 needs — no deadsnakes,
no source build.

Run everything as a sudo-capable user unless a step says otherwise.

---

## 1. System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    python3.12 python3.12-venv python3-pip \
    postgresql postgresql-contrib \
    nginx git curl \
    build-essential libpq-dev
```

`postgresql-contrib` matters: it carries `pg_trgm`, which the search migration
needs. Without it that migration fails with *"extension is not available"*.

---

## 2. App user and directories

The app runs as its own unprivileged user. Its **group is `www-data`** so nginx
can read `static/` and `media/` without those directories being world-readable.

```bash
sudo useradd --system --create-home --home-dir /srv/archethos --shell /bin/bash archethos
sudo usermod -aG www-data archethos

sudo mkdir -p /var/www/api.archethos.com
sudo chown archethos:www-data /srv/archethos /var/www/api.archethos.com
sudo chmod 750 /srv/archethos /var/www/api.archethos.com
```

Two locations, on purpose:

| | |
|---|---|
| `/var/www/api.archethos.com` | the code, and the `static/` and `media/` nginx serves |
| `/srv/archethos` | the user's **home** — deploy key (`.ssh/`) and `.pgpass` |

The secrets stay out of the directory nginx serves from. nginx is configured
with `alias` on two specific sub-paths rather than a `root`, so nothing else is
reachable — but if a later change ever adds a `root` or a stray `location /`,
the difference between "leaked a stylesheet" and "leaked the deploy key" is this
separation.

---

## 3. PostgreSQL

```bash
sudo -u postgres psql <<'SQL'
CREATE USER archethos WITH PASSWORD 'CHANGE-ME-strong-password';
CREATE DATABASE archethos OWNER archethos;

-- Sane session defaults for a Django app.
ALTER ROLE archethos SET client_encoding TO 'utf8';
ALTER ROLE archethos SET default_transaction_isolation TO 'read committed';
ALTER ROLE archethos SET timezone TO 'UTC';
SQL
```

Now create the extensions **as the superuser**, before the app ever migrates:

```bash
sudo -u postgres psql -d archethos <<'SQL'
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
SQL
```

> **Why by hand.** `CREATE EXTENSION` requires superuser, and the app role is
> deliberately not one. Django's migration uses `IF NOT EXISTS`, so once these
> exist it becomes a harmless no-op and `migrate` succeeds as `archethos`. Skip
> this and `content.0003_search_extensions` fails with a permission error.

---

## 4. Get the code

The repository is private, so give the server a **read-only deploy key** rather
than putting a personal token on disk.

```bash
sudo -u archethos ssh-keygen -t ed25519 -C "archethos-vps" -f /srv/archethos/.ssh/id_ed25519 -N ""
sudo -u archethos cat /srv/archethos/.ssh/id_ed25519.pub
```

Add that public key at **GitHub → repo → Settings → Deploy keys → Add**, leaving
*Allow write access* **unchecked**. Verify it before cloning — this fails fast
and unambiguously if the key was not accepted:

```bash
sudo -u archethos ssh -T git@github.com
# "Hi JS-TECHNOVA/api.archethos.com! You've successfully authenticated…"
```

Then clone. `/var/www/api.archethos.com` already exists, and `git clone` refuses
a directory that is not empty, so clone **into** it:

```bash
cd /var/www/api.archethos.com
sudo -u archethos git clone git@github.com:JS-TECHNOVA/api.archethos.com.git .
```

If it still refuses because something is in there (an nginx placeholder
`index.html` is the usual culprit), check what and clear it:

```bash
ls -la /var/www/api.archethos.com
sudo rm -f /var/www/api.archethos.com/index.html
```

---

## 5. Virtualenv

```bash
sudo -u archethos python3.12 -m venv /var/www/api.archethos.com/.venv
sudo -u archethos /var/www/api.archethos.com/.venv/bin/pip install --upgrade pip
sudo -u archethos /var/www/api.archethos.com/.venv/bin/pip install -r /var/www/api.archethos.com/requirements/prod.txt
```

---

## 6. Environment

```bash
sudo -u archethos cp /var/www/api.archethos.com/.env.production.example /var/www/api.archethos.com/.env
sudo -u archethos nano /var/www/api.archethos.com/.env
sudo chmod 600 /var/www/api.archethos.com/.env
```

Two values must be changed before anything else:

```bash
# A key that has never existed anywhere else.
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

- `SECRET_KEY` — the generated value. **Never reuse the development key**:
  it signs every session token, and it is in your dev `.env` and in shell
  history.
- `DB_PASSWORD` — what you set in step 3.

Everything else in the template is already correct for this host.

---

## 7. First run

```bash
cd /var/www/api.archethos.com/archethosbackend
export DJANGO_SETTINGS_MODULE=archethosbackend.settings.production
V=/var/www/api.archethos.com/.venv/bin/python

sudo -u archethos --preserve-env=DJANGO_SETTINGS_MODULE $V manage.py check --deploy
sudo -u archethos --preserve-env=DJANGO_SETTINGS_MODULE $V manage.py migrate
sudo -u archethos --preserve-env=DJANGO_SETTINGS_MODULE $V manage.py collectstatic --no-input
sudo -u archethos --preserve-env=DJANGO_SETTINGS_MODULE $V manage.py sync_cms_groups
sudo -u archethos --preserve-env=DJANGO_SETTINGS_MODULE $V manage.py createsuperuser
```

`migrate` seeds the ten `Page` rows and the four CMS roles. `createsuperuser`
asks for a username and email — you will be able to sign in with **either**.

Media directory, writable by the app and readable by nginx:

```bash
sudo -u archethos mkdir -p /var/www/api.archethos.com/media/uploads
sudo chown -R archethos:www-data /var/www/api.archethos.com/media /var/www/api.archethos.com/staticfiles
sudo chmod -R 750 /var/www/api.archethos.com/media /var/www/api.archethos.com/staticfiles
```

---

## 8. gunicorn

```bash
sudo cp /var/www/api.archethos.com/deploy/gunicorn.service /etc/systemd/system/archethos-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now archethos-api
systemctl status archethos-api --no-pager
```

Check it answers on the socket before involving nginx — that separates "the app
is broken" from "the proxy is misconfigured":

```bash
sudo -u www-data curl --unix-socket /run/archethos/gunicorn.sock http://localhost/health/
# {"success":true,...,"data":{"status":"ok","database":"ok"}}
```

Let the deploy script reload the service without a password prompt:

```bash
echo 'archethos ALL=(root) NOPASSWD: /usr/bin/systemctl reload archethos-api' \
  | sudo tee /etc/sudoers.d/archethos-deploy
sudo chmod 440 /etc/sudoers.d/archethos-deploy
```

---

## 9. nginx and TLS

Point `api.archethos.com`'s **A record** at this server first, and wait for it
to resolve — certbot validates over HTTP and will fail otherwise.

```bash
sudo mkdir -p /var/www/certbot
sudo cp /var/www/api.archethos.com/deploy/nginx.conf /etc/nginx/sites-available/api.archethos.com
sudo ln -sf /etc/nginx/sites-available/api.archethos.com /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

The shipped file has its `ssl_certificate` lines commented out, so nginx will
not start with the 443 block yet. Comment out the whole `server { listen 443 ... }`
block, start nginx on port 80, then let certbot write the TLS config:

```bash
sudo nginx -t && sudo systemctl restart nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.archethos.com --agree-tos -m you@example.com --redirect
```

certbot rewrites the file with real certificate paths and a redirect. Then
restore the tuned directives it does not add — `client_max_body_size 25M;` and
the `/static/` and `/media/` blocks — into the 443 server it produced, and:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

> **`client_max_body_size` is the one people lose.** nginx defaults to 1 MB and
> answers **413** before Django sees the request, so a 20 MB upload fails with
> no Django log line and looks like a broken endpoint. It must be above
> `MAX_UPLOAD_SIZE_MB` so Django owns the rejection and can explain it.

Renewal is automatic via certbot's systemd timer — confirm with:

```bash
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

---

## 10. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

PostgreSQL stays closed to the internet — Django reaches it on localhost.

---

## 11. Verify

```bash
curl https://api.archethos.com/health/
curl -i https://api.archethos.com/api/v1/public/pages/home/     # 404 until published
curl https://api.archethos.com/api/v1/public/company/
```

Then the auth flow, which is what actually exercises cookies and CSRF:

```bash
curl -c /tmp/j -s https://api.archethos.com/api/v1/auth/csrf/ >/dev/null
CSRF=$(grep csrftoken /tmp/j | awk '{print $7}')
curl -b /tmp/j -c /tmp/j -H "X-CSRFToken: $CSRF" -H 'Content-Type: application/json' \
     -d '{"email":"you@example.com","password":"..."}' \
     https://api.archethos.com/api/v1/auth/login/
curl -b /tmp/j https://api.archethos.com/api/v1/auth/me/
```

Check the login response carries `Secure` and `HttpOnly` on both cookies. If it
does not, `SECURE_PROXY_SSL_HEADER` is not seeing nginx's `X-Forwarded-Proto`.

---

## 12. Backups

The database and `media/` are the only irreplaceable things on this box — the
code is in git and can be re-cloned.

```bash
sudo mkdir -p /var/backups/archethos && sudo chown archethos: /var/backups/archethos

sudo -u archethos crontab -e
```

```cron
# Database, nightly, kept 14 days.
0 2 * * * pg_dump -U archethos -h localhost archethos | gzip > /var/backups/archethos/db-$(date +\%F).sql.gz && find /var/backups/archethos -name 'db-*.sql.gz' -mtime +14 -delete

# Uploaded media, weekly.
0 3 * * 0 tar czf /var/backups/archethos/media-$(date +\%F).tar.gz -C /var/www/api.archethos.com media
```

`pg_dump` needs the password — put it in `/srv/archethos/.pgpass` (`chmod 600`)
as `localhost:5432:archethos:archethos:YOUR-PASSWORD`.

> **Copy these off the machine.** A backup on the same disk as the thing it
> backs up protects against a bad migration, not against losing the server.

---

## 13. Deploying a change

From then on, a deploy is one command:

```bash
sudo -u archethos /var/www/api.archethos.com/deploy/deploy.sh
```

It fetches `main`, installs dependencies, **refuses to continue if a model was
changed without a migration**, runs `check --deploy`, migrates, collects static,
syncs roles, reloads gunicorn gracefully, and polls `/health/`. It stops at the
first failure, so a failed migration is never followed by a reload that puts new
code against an old schema.

**Never run `makemigrations` on the server.** Migrations are committed from
development, reviewed, and applied here. `sections/0002_hero_variant_and_dual_cta.py`
is the reason: it renames a column, and a non-interactive `makemigrations` would
answer "no" to the rename prompt and silently drop the data instead.

---

## 14. When something breaks

```bash
journalctl -u archethos-api -n 100 --no-pager     # app logs
sudo tail -50 /var/log/nginx/archethos-api.error.log
sudo systemctl status archethos-api nginx postgresql
```

| Symptom | Cause |
|---|---|
| **502 Bad Gateway** | gunicorn is down, or nginx cannot read the socket. Check `journalctl -u archethos-api`, then that `www-data` is in the right group. |
| **413 on upload** | `client_max_body_size` — certbot's rewrite dropped it. |
| **Infinite redirect loop** | nginx is not sending `X-Forwarded-Proto`, so Django keeps redirecting to HTTPS. |
| **403 CSRF on login** | The origin is missing from `CSRF_TRUSTED_ORIGINS`. |
| **CORS error in the browser** | The frontend origin is missing from `CORS_ALLOWED_ORIGINS` — and it must be exact, scheme included. |
| **Cookies set but never sent back** | `AUTH_COOKIE_SECURE=True` over plain HTTP, or a frontend fetch without `credentials: "include"`. |
| **`permission denied to create extension`** | Step 3's manual `CREATE EXTENSION` was skipped. |
| **Static files 404 / unstyled admin** | `collectstatic` not run, or `staticfiles/` not readable by `www-data`. |

---

## What this does not cover

- **Log rotation for gunicorn** — output goes to journald, which rotates itself.
  nginx logs rotate via the packaged logrotate config.
- **Monitoring/alerting.** `/health/` returns 200 with `{"database":"ok"}` and
  503 when Postgres is unreachable — point an uptime check at it.
- **Zero-downtime schema changes.** `deploy.sh` migrates then reloads, so a
  destructive migration is briefly live against old code. For anything that
  drops or renames a column, deploy in two passes: add, ship code, then remove.
- **Object storage.** Media is on local disk, which is what `media_location`
  tracks. Moving to S3 later is a settings change plus a batch move; nothing in
  the database stores an absolute URL, so no content rows change.
