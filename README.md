# Splatter API

Canonical public contract for the Splatter HTTP API.

The first supported external workflow creates a splat, uploads a large source directly through
short-lived presigned URLs, completes the upload, and lets Splatter begin processing. Splat listing
is not part of the first external contract.

## Standalone Python uploader

The repository includes a dependency-free Python 3.10+ upload tool. It does not need installation
or packaging.

Create a personal token on the Splatter Settings page, then upload a PLY source:

```bash
export SPLATTER_TOKEN='splatter_v1_...'
python3 splatter-upload.py scan.ply
```

The tool reads the Gaussian count from the PLY header, streams file ranges directly to short-lived
part URLs, completes the upload, and waits for processing to reach `ready` or `failed`. A failed
storage part is authorized again and retried until it succeeds or the command is interrupted. Other
API requests are not retried, and the tool does not create resume checkpoints; rerunning an
interrupted command starts a new splat and upload.

Use `--no-wait` to return after upload completion, `--workers` to control parallel uploads, and
`--api-origin` for a non-production environment. Run `python3 splatter-upload.py --help` for all
options.

Run the dependency-free test suite from the repository root with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

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
