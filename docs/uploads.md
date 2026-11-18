# Uploads

1. Inspect the source locally and obtain its byte size and Gaussian count.
2. Create the splat with `POST /api/v1/splats` and a unique `Idempotency-Key`.
3. Divide the file according to the returned `partSizeBytes` and `partCount`.
4. Request up to 16 presigned URLs at a time from the part-authorization endpoint.
5. `PUT` each part directly to its URL and retain the HTTP `ETag` response header.
6. Submit every `{ partNumber, etag }` pair in ascending order to the completion endpoint.

Part numbering starts at 1. Every part except the last is exactly `partSizeBytes`; the last contains
the remainder. Expired URLs can be requested again safely. Parts may be uploaded concurrently.

Only PLY is accepted today. Clients obtain `source.gaussianCount` from the PLY vertex declaration,
but the API treats it as a format-independent, unverified source count.
