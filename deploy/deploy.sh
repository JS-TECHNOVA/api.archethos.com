#!/usr/bin/env bash
#
# Deploy the current main branch.
#
#   sudo -u archethos /srv/archethos/api/deploy/deploy.sh
#
# Safe to re-run. Every step is idempotent, and the script stops at the first
# failure rather than half-deploying — a failed migrate must not be followed by
# a reload that puts new code against an old schema.

set -euo pipefail

APP_DIR="/srv/archethos/api"
VENV="$APP_DIR/.venv"
MANAGE="$VENV/bin/python $APP_DIR/archethosbackend/manage.py"
SERVICE="archethos-api"

export DJANGO_SETTINGS_MODULE="archethosbackend.settings.production"

say() { printf '\n\033[1m── %s\033[0m\n' "$1"; }

cd "$APP_DIR"

say "Fetching main"
git fetch --prune origin
git reset --hard origin/main
git log -1 --format='  %h  %s'

say "Installing dependencies"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r requirements/prod.txt

say "Checking for a model change with no migration"
# Catches the case where a model was edited but makemigrations was never run.
# Better to fail here than to have Django and Postgres disagree at runtime.
$MANAGE makemigrations --check --dry-run --no-input

say "Running deployment checks"
$MANAGE check --deploy --fail-level WARNING

say "Applying migrations"
$MANAGE migrate --no-input

say "Collecting static files"
$MANAGE collectstatic --no-input --clear

say "Syncing CMS roles"
# Roles grant whatever models exist when they are synced, so this has to run
# after migrate on any deploy that added a model.
$MANAGE sync_cms_groups

say "Reloading gunicorn"
# HUP, not restart: in-flight requests finish before workers are swapped.
sudo systemctl reload "$SERVICE"

say "Verifying"
sleep 2
for attempt in $(seq 1 10); do
    if curl -fsS --max-time 5 https://api.archethos.com/health/ >/dev/null 2>&1; then
        curl -s https://api.archethos.com/health/
        printf '\n\033[1;32m  Deployed.\033[0m\n'
        exit 0
    fi
    sleep 2
done

printf '\n\033[1;31m  Health check failed after reload.\033[0m\n'
printf '  journalctl -u %s -n 50 --no-pager\n' "$SERVICE"
exit 1
