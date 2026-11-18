# Idempotency

`POST /api/v1/splats` requires an `Idempotency-Key` containing 8–128 URL-safe characters. Keys are
scoped to the authenticated user.

Replaying the same key with the same semantic request returns the existing splat and upload policy.
Reusing it for a different request returns `409` and creates nothing. Generate one key per logical
upload and retain it until creation succeeds or fails definitively.

Upload completion is idempotent from persisted application state and does not take an idempotency
header.
