#!/bin/sh
set -eu

compose_file="$(dirname "$0")/compose.yaml"

docker compose -f "$compose_file" down
if docker volume inspect farmfinder_postgres-data >/dev/null 2>&1; then
  docker volume rm farmfinder_postgres-data
fi

echo "PostgreSQL volume removed. The versioned object-storage volume was preserved."
