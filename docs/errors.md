# Errors

Every error response uses the same envelope:

```json
{
  "error": {
    "code": "UPLOAD_STATE_CONFLICT",
    "message": "Upload cannot be completed",
    "requestId": "cli-20261119-01"
  }
}
```

`code` is the stable machine-readable value. `message` is safe to show to a person but is not a
control-flow contract. Validation failures may include `error.fields`, an array of `path` and
`message` objects.

Every response includes `X-Request-Id`. On errors it matches `error.requestId`. A client may send an
`X-Request-Id` containing 8–128 ASCII letters, digits, `.`, `_`, `:`, or `-`; the server replaces
missing or invalid values. Include the response request ID in support reports, but do not include
credentials or presigned URLs.

Current codes are:

- `AUTHENTICATION_REQUIRED`
- `IDEMPOTENCY_CONFLICT`
- `INTERNAL_ERROR`
- `INVALID_REQUEST`
- `MALFORMED_JSON`
- `RATE_LIMITED`
- `SPLAT_NOT_FOUND`
- `TEMPORARY_UNAVAILABLE`
- `UNSUPPORTED_MEDIA_TYPE`
- `UPLOAD_STATE_CONFLICT`
- `UPSTREAM_FAILURE`

Treat `400`, `404`, and most `409` responses as terminal. Retry `429`, `502`, and `503` with capped
exponential backoff and jitter. For `429`, wait at least the number of seconds in `Retry-After`. Do
not retry an invalid `401` credential indefinitely. Operation-specific retry guidance is in
[Uploads](uploads.md).
