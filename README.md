# Splatter API

The Splatter API lets you upload PLY sources, track their processing, and manage the resulting 3D
scenes from your own tools and workflows.

## Standalone Python uploader

The repository includes a dependency-free Python 3.10+ upload tool. It does not need installation
or packaging.

### Usage

Create a personal token on the Splatter Settings page and provide it through `SPLATTER_TOKEN`, then
pass the path of a PLY file to the script:

```bash
export SPLATTER_TOKEN='splatter_v1_...'
python3 splatter-upload.py scan.ply
```

Uploads are unlisted by default, and the command waits until processing finishes. Common options
include:

```bash
# Set the scene title and make it public
python3 splatter-upload.py scan.ply --title 'My scan' --visibility public

# Return as soon as the source upload is complete
python3 splatter-upload.py scan.ply --no-wait
```

Progress is written to standard error. The final public ID and status are printed as JSON to
standard output. Run `python3 splatter-upload.py --help` to see every option.

The tool reads the Gaussian count from the PLY header, streams file ranges directly to short-lived
part URLs, completes the upload, and waits for processing to reach `ready` or `failed`. A failed
storage part is authorized again and retried until it succeeds or the command is interrupted. Other
API requests are not retried, and the tool does not create resume checkpoints; rerunning an
interrupted command starts a new splat and upload.

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
