#!/bin/sh
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
site_root="$(dirname "$script_dir")"
compose_file="$script_dir/compose.yaml"
database="${POSTGRES_DB:-farmfinder}"
user="${POSTGRES_USER:-farmfinder}"

for test_file in foundation.sql discovery.sql; do
  docker compose -f "$compose_file" exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U "$user" -d "$database" \
    < "$site_root/packages/db/tests/$test_file"
done
