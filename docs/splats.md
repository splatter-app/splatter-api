# Splat resources

All splat resources are scoped to the authenticated owner.

- `GET /api/v1/splats/{publicId}` returns status and editable metadata. Its `scene` field is null
  until the splat is ready.
- `PATCH /api/v1/splats/{publicId}` updates one or more of `title`, `description`, `visibility`, and
  `viewerConfig` atomically. Viewer configuration can only be updated after processing is ready.
- `DELETE /api/v1/splats/{publicId}` soft-deletes the splat and returns `204`.
- `DELETE /api/v1/splats` accepts 1–250 unique public IDs and atomically soft-deletes the complete
  owned set. It returns `204` only when every requested splat is active and owned.

The external contract does not currently have a list operation. Clients retain the `publicId`
returned by creation and use it for polling and later operations. A future list operation will use
bounded cursor pagination and stable summary resources rather than the website dashboard shape.

Missing, deleted, malformed, and non-owned public IDs use the same `404` response. Clients must not
use that response to infer whether another user owns an identifier.

Bulk deletion follows the same rule for the complete request: if any public ID is missing, deleted,
malformed, or non-owned, no splats are deleted and the endpoint returns `404`.

Example metadata update:

```http
PATCH /api/v1/splats/abc-123-xyz
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "title": "Courtyard at dusk",
  "description": "Captured after sunset",
  "visibility": "unlisted"
}
```
