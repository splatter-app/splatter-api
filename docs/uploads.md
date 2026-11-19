# Uploads

1. Inspect the source locally and obtain its byte size and Gaussian count.
2. Create the splat with `POST /api/v1/splats` and a unique `Idempotency-Key`.
3. Divide the file according to the returned `partSizeBytes` and `partCount`.
4. Request up to 16 presigned URLs at a time from the part-authorization endpoint.
5. `PUT` each part directly to its URL and retain the HTTP `ETag` response header.
6. Submit every `{ partNumber, etag }` pair in ascending order to the completion endpoint.
7. Poll `GET /api/v1/splats/{publicId}` until `splat.status` is `ready` or `failed`.

Part numbering starts at 1. Every part except the last is exactly `partSizeBytes`; the last contains
the remainder. Expired URLs can be requested again safely. Parts may be uploaded concurrently.

Only PLY is accepted today. Clients obtain `source.gaussianCount` from the PLY vertex declaration,
but the API treats it as a format-independent, unverified source count.

## Limits

- Source files contain at most 4,000 parts of 128 MB each (500 GB total).
- A part-authorization request contains 1–16 unique part numbers from the upload policy.
- Part URLs expire after 15 minutes. Request a replacement authorization instead of retaining an
  expired URL.
- Completion contains exactly one ETag for every part in the upload policy.
- Per owner and per Cloudflare location, the API approximately permits 10 creations, 120
  part-authorization requests, and 20 completions per 60 seconds. A rejected request returns `429`
  with `Retry-After: 60`; these abuse controls are not strict global quotas.

## Retries

- Retry creation with the same `Idempotency-Key` and identical JSON. Never generate a new key for
  an ambiguous creation failure.
- Part authorization and status polling are safe to repeat. Use capped exponential backoff for
  transient network errors and `502` or `503` responses.
- Retry a failed storage `PUT` for the same part number. Request a new URL first when the previous
  URL may have expired. Never send the Splatter bearer token to that URL.
- Upload completion is idempotent from persisted upload state and is safe to repeat with the same
  complete part list.
- Treat `400`, `401`, `404`, and most `409` responses as terminal. A `401` from a personal token
  requires replacing or renewing the token, not an unbounded retry loop.
- On `429`, wait at least the number of seconds in `Retry-After` before retrying.

The [curl example](../examples/curl/upload.sh) implements the complete create, upload, completion,
and polling flow. A production CLI should add bounded retry delays and persist the idempotency key,
public ID, upload policy, and completed ETags until the upload reaches a terminal state.
