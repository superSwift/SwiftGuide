#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <backup.sql.gz>"
  exit 1
fi

: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGUSER:=quant}"
: "${PGDATABASE:=quant}"

BACKUP_FILE="$1"
gzip -dc "$BACKUP_FILE" | psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE"
echo "restore completed from: $BACKUP_FILE"
