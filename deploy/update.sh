#!/bin/sh
# Runs ON THE SERVER: pull the latest code from GitHub and rebuild the container.
#   /srv/citymaps/deploy/update.sh
# The OSM download cache (Docker volume "citymaps_osm-cache") is kept.
set -e
cd "$(dirname "$0")/.."
git fetch --quiet origin main
git reset --hard --quiet origin/main     # the server copy always mirrors GitHub
echo "==> Code at $(git log -1 --format='%h %s')"
docker compose up -d --build --remove-orphans
docker image prune -f >/dev/null
sleep 5
docker compose ps
