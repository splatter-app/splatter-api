# Splatter API

Canonical public contract for the Splatter HTTP API.

The first supported external workflow creates a splat, uploads a large source directly through
short-lived presigned URLs, completes the upload, and lets Splatter begin processing. Splat listing
is not part of the first external contract.

## Documentation

- [OpenAPI contract](openapi.yaml)
- [Authentication](docs/authentication.md)
- [Uploads](docs/uploads.md)
- [Splat resources](docs/splats.md)
- [Errors](docs/errors.md)
- [Idempotency](docs/idempotency.md)
- [Versioning](docs/versioning.md)
- [curl upload example](examples/curl/upload.sh)

Only PLY sources are currently accepted. The source request uses a format-independent
`gaussianCount`; obtaining that value from a PLY vertex declaration is a client implementation
detail.
