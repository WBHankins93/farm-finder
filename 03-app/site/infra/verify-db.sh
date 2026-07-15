#!/bin/sh
set -eu

compose_file="$(dirname "$0")/compose.yaml"
database="${POSTGRES_DB:-farmfinder}"
user="${POSTGRES_USER:-farmfinder}"

docker compose -f "$compose_file" exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U "$user" -d "$database" -f /verify/verify.sql
