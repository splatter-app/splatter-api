#!/usr/bin/env bash
set -euo pipefail

# Documentation example: requires curl, jq, split, and a valid current bearer token.
# Usage: SPLATTER_TOKEN=... ./examples/curl/upload.sh source.ply 4200000

source_file=${1:?source PLY path is required}
gaussian_count=${2:?source Gaussian count is required}
api_origin=${SPLATTER_API_ORIGIN:-https://new.splatter.app/api/v1}
source_size=$(wc -c < "$source_file" | tr -d ' ')
source_name=$(basename "$source_file")
idempotency_key=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')

creation=$(curl --fail-with-body --silent --show-error \
  --request POST "$api_origin/splats" \
  --header "Authorization: Bearer $SPLATTER_TOKEN" \
  --header "Content-Type: application/json" \
  --header "Idempotency-Key: $idempotency_key" \
  --data "$(jq -n \
    --arg filename "$source_name" \
    --argjson sizeBytes "$source_size" \
    --argjson gaussianCount "$gaussian_count" \
    '{title: $filename, description: null, visibility: "unlisted", source: {filename: $filename, format: "ply", sizeBytes: $sizeBytes, gaussianCount: $gaussianCount}}')")

public_id=$(jq -r '.splat.publicId' <<< "$creation")
part_size=$(jq -r '.upload.partSizeBytes' <<< "$creation")
part_count=$(jq -r '.upload.partCount' <<< "$creation")
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT
split --bytes="$part_size" --numeric-suffixes=1 --suffix-length=4 "$source_file" "$work_dir/part-"

completion_parts='[]'
for part_number in $(seq 1 "$part_count"); do
  authorization=$(curl --fail-with-body --silent --show-error \
    --request POST "$api_origin/splats/$public_id/upload/part-authorizations" \
    --header "Authorization: Bearer $SPLATTER_TOKEN" \
    --header "Content-Type: application/json" \
    --data "{\"partNumbers\":[$part_number]}")
  upload_url=$(jq -r '.parts[0].url' <<< "$authorization")
  part_path=$(printf '%s/part-%04d' "$work_dir" "$part_number")
  headers=$(mktemp "$work_dir/headers.XXXXXX")
  curl --fail-with-body --silent --show-error \
    --request PUT "$upload_url" \
    --dump-header "$headers" \
    --upload-file "$part_path" \
    --output /dev/null
  etag=$(awk 'BEGIN { IGNORECASE=1 } /^etag:/ { sub(/^[^:]+:[[:space:]]*/, ""); sub(/\r$/, ""); print; exit }' "$headers")
  completion_parts=$(jq --argjson partNumber "$part_number" --arg etag "$etag" \
    '. + [{partNumber: $partNumber, etag: $etag}]' <<< "$completion_parts")
done

curl --fail-with-body --silent --show-error \
  --request POST "$api_origin/splats/$public_id/upload/completion" \
  --header "Authorization: Bearer $SPLATTER_TOKEN" \
  --header "Content-Type: application/json" \
  --data "$(jq -n --argjson parts "$completion_parts" '{parts: $parts}')"
