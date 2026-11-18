# Errors

The first contract returns a safe JSON `error` string and, for validation failures, optional field
details. Stable machine-readable error codes and request IDs are planned for the remaining v1 route
cleanup.

Clients should treat `400`, `404`, and most `409` responses as terminal. Retry `502` and `503` with
capped exponential backoff. Do not retry an invalid `401` credential indefinitely.
