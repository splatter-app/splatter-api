#!/usr/bin/env python3
"""Upload one PLY source through the Splatter public API."""

from __future__ import annotations

import argparse
import concurrent.futures
import getpass
import http.client
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, BinaryIO, Callable
import urllib.error
import urllib.parse
import urllib.request
import uuid


DEFAULT_API_ORIGIN = "https://new.splatter.app/api/v1"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_PLY_HEADER_BYTES = 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024


class UploadError(Exception):
    """A user-facing upload failure."""


class ApiError(UploadError):
    def __init__(
        self,
        status: int,
        message: str,
        *,
        code: str | None = None,
        request_id: str | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.request_id = request_id
        self.retry_after = retry_after

    def __str__(self) -> str:
        details = [f"API request failed ({self.status})"]
        if self.code:
            details.append(self.code)
        details.append(super().__str__())
        if self.request_id:
            details.append(f"request ID: {self.request_id}")
        if self.retry_after:
            details.append(f"retry after: {self.retry_after}s")
        return "; ".join(details)


def inspect_ply(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
    except OSError as error:
        raise UploadError(f"cannot read {path}: {error}") from error
    if not path.is_file() or stat.st_size <= 0:
        raise UploadError("source must be a non-empty regular file")

    vertex_count: int | None = None
    header_size = 0
    try:
        with path.open("rb") as source:
            first_line = source.readline(MAX_PLY_HEADER_BYTES + 1)
            header_size += len(first_line)
            if first_line.rstrip(b"\r\n") != b"ply":
                raise UploadError("source is not a PLY file")

            while header_size <= MAX_PLY_HEADER_BYTES:
                line = source.readline(MAX_PLY_HEADER_BYTES - header_size + 1)
                if not line:
                    break
                header_size += len(line)
                try:
                    text = line.decode("ascii").strip()
                except UnicodeDecodeError as error:
                    raise UploadError("PLY header must be ASCII") from error
                fields = text.split()
                if len(fields) == 3 and fields[:2] == ["element", "vertex"]:
                    try:
                        vertex_count = int(fields[2])
                    except ValueError as error:
                        raise UploadError("PLY vertex count is not an integer") from error
                if text == "end_header":
                    if vertex_count is None or vertex_count <= 0:
                        raise UploadError("PLY header has no positive vertex count")
                    return stat.st_size, vertex_count
    except OSError as error:
        raise UploadError(f"cannot read {path}: {error}") from error

    raise UploadError("PLY header is missing end_header or exceeds 1 MB")


class ApiClient:
    def __init__(self, origin: str, token: str, timeout: float = 60.0) -> None:
        self.origin = origin.rstrip("/")
        self.token = token
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "splatter-upload/1",
        }
        if data is not None:
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            f"{self.origin}{path}", data=data, headers=request_headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return self._read_json(response)
        except urllib.error.HTTPError as error:
            payload = self._read_error(error)
            api_error = payload.get("error", {}) if isinstance(payload, dict) else {}
            message = api_error.get("message") or error.reason or "unknown API error"
            raise ApiError(
                error.code,
                str(message),
                code=api_error.get("code"),
                request_id=api_error.get("requestId") or error.headers.get("X-Request-Id"),
                retry_after=error.headers.get("Retry-After"),
            ) from error
        except urllib.error.URLError as error:
            raise UploadError(f"API request failed: {error.reason}") from error

    @staticmethod
    def _read_json(response: Any) -> dict[str, Any]:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise UploadError("API response exceeded 1 MB")
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UploadError("API returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise UploadError("API returned an unexpected response")
        return payload

    @staticmethod
    def _read_error(error: urllib.error.HTTPError) -> dict[str, Any]:
        try:
            raw = error.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) <= MAX_RESPONSE_BYTES:
                payload = json.loads(raw)
                return payload if isinstance(payload, dict) else {}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        return {}

    def create(
        self,
        path: Path,
        size: int,
        gaussian_count: int,
        title: str,
        description: str | None,
        visibility: str,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            "/splats",
            {
                "title": title,
                "description": description,
                "visibility": visibility,
                "source": {
                    "filename": path.name,
                    "format": "ply",
                    "sizeBytes": size,
                    "gaussianCount": gaussian_count,
                },
            },
            {"Idempotency-Key": str(uuid.uuid4())},
        )

    def authorize(self, public_id: str, part_numbers: list[int]) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/splats/{urllib.parse.quote(public_id, safe='')}/upload/part-authorizations",
            {"partNumbers": part_numbers},
        )

    def complete(self, public_id: str, parts: list[dict[str, Any]]) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/splats/{urllib.parse.quote(public_id, safe='')}/upload/completion",
            {"parts": parts},
        )

    def get(self, public_id: str) -> dict[str, Any]:
        return self.request("GET", f"/splats/{urllib.parse.quote(public_id, safe='')}")


def _send_range(connection: http.client.HTTPConnection, source: BinaryIO, length: int) -> None:
    remaining = length
    while remaining:
        chunk = source.read(min(remaining, UPLOAD_CHUNK_BYTES))
        if not chunk:
            raise UploadError("source changed or ended during upload")
        connection.send(chunk)
        remaining -= len(chunk)


def put_file_part(url: str, path: Path, offset: int, length: int, timeout: float = 300.0) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UploadError("part authorization returned an invalid URL")
    connection_type = (
        http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    )
    port = parsed.port
    connection = connection_type(parsed.hostname, port=port, timeout=timeout)
    target = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    try:
        connection.putrequest("PUT", target)
        connection.putheader("Content-Length", str(length))
        connection.endheaders()
        with path.open("rb") as source:
            source.seek(offset)
            _send_range(connection, source, length)
        response = connection.getresponse()
        response.read(MAX_RESPONSE_BYTES + 1)
        if not 200 <= response.status < 300:
            raise UploadError(f"storage returned HTTP {response.status}")
        etag = response.getheader("ETag")
        if not etag:
            raise UploadError("storage response did not include ETag")
        return etag
    except (OSError, http.client.HTTPException) as error:
        raise UploadError(f"part transfer failed: {error}") from error
    finally:
        connection.close()


def upload_parts(
    client: ApiClient,
    public_id: str,
    path: Path,
    size: int,
    part_size: int,
    part_count: int,
    workers: int,
    put_part: Callable[[str, Path, int, int], str] = put_file_part,
) -> list[dict[str, Any]]:
    etags: dict[int, str] = {}
    for start in range(1, part_count + 1, 16):
        pending = list(range(start, min(start + 16, part_count + 1)))
        while pending:
            response = client.authorize(public_id, pending)
            authorizations = {
                int(item["partNumber"]): str(item["url"])
                for item in response.get("parts", [])
                if isinstance(item, dict) and "partNumber" in item and "url" in item
            }
            if set(authorizations) != set(pending):
                raise UploadError("part authorization response did not match the request")

            failed: list[int] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, len(pending))) as pool:
                futures = {}
                for part_number in pending:
                    offset = (part_number - 1) * part_size
                    length = min(part_size, size - offset)
                    futures[pool.submit(put_part, authorizations[part_number], path, offset, length)] = (
                        part_number
                    )
                for future in concurrent.futures.as_completed(futures):
                    part_number = futures[future]
                    try:
                        etags[part_number] = future.result()
                        print(f"uploaded part {part_number}/{part_count}", file=sys.stderr)
                    except Exception as error:
                        failed.append(part_number)
                        print(f"part {part_number} failed: {error}", file=sys.stderr)
            pending = sorted(failed)
            if pending:
                print(
                    f"retrying {len(pending)} failed part(s) with fresh authorization",
                    file=sys.stderr,
                )
                time.sleep(1)

    return [{"partNumber": number, "etag": etags[number]} for number in range(1, part_count + 1)]


def run_upload(
    client: ApiClient,
    path: Path,
    *,
    title: str,
    description: str | None,
    visibility: str,
    workers: int,
    wait: bool,
    poll_interval: float,
    put_part: Callable[[str, Path, int, int], str] = put_file_part,
) -> dict[str, str]:
    size, gaussian_count = inspect_ply(path)
    creation = client.create(path, size, gaussian_count, title, description, visibility)
    try:
        public_id = str(creation["splat"]["publicId"])
        part_size = int(creation["upload"]["partSizeBytes"])
        part_count = int(creation["upload"]["partCount"])
    except (KeyError, TypeError, ValueError) as error:
        raise UploadError("create response was missing upload details") from error
    if (
        part_size <= 0
        or part_count <= 0
        or part_count != (size + part_size - 1) // part_size
    ):
        raise UploadError("create response contained an invalid upload policy")

    print(f"created {public_id}; uploading {part_count} part(s)", file=sys.stderr)
    parts = upload_parts(
        client, public_id, path, size, part_size, part_count, workers, put_part=put_part
    )
    completion = client.complete(public_id, parts)
    try:
        status = str(completion["splat"]["status"])
    except (KeyError, TypeError) as error:
        raise UploadError("completion response was missing splat status") from error

    if wait:
        while status not in {"ready", "failed"}:
            time.sleep(poll_interval)
            detail = client.get(public_id)
            try:
                status = str(detail["splat"]["status"])
            except (KeyError, TypeError) as error:
                raise UploadError("status response was missing splat status") from error
            print(f"{public_id}: {status}", file=sys.stderr)
    return {"publicId": public_id, "status": status}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="PLY source file")
    parser.add_argument(
        "--api-origin", default=os.environ.get("SPLATTER_API_ORIGIN", DEFAULT_API_ORIGIN)
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("SPLATTER_TOKEN"),
        help="personal API token (defaults to SPLATTER_TOKEN or a secure prompt)",
    )
    parser.add_argument("--title", help="splat title (defaults to the filename)")
    parser.add_argument("--description")
    parser.add_argument("--visibility", choices=("public", "unlisted"), default="unlisted")
    parser.add_argument("--workers", type=int, choices=range(1, 17), default=4, metavar="1-16")
    parser.add_argument("--poll-interval", type=float, default=5.0, metavar="SECONDS")
    parser.add_argument("--no-wait", action="store_true", help="return after upload completion")
    args = parser.parse_args(argv)
    if not args.token:
        if not sys.stdin.isatty():
            parser.error("set SPLATTER_TOKEN or pass --token in non-interactive environments")
        try:
            args.token = getpass.getpass("Splatter token: ").strip()
        except KeyboardInterrupt:
            parser.exit(130, "\ntoken entry interrupted\n")
        except EOFError:
            parser.error("could not read a token; set SPLATTER_TOKEN or pass --token")
        if not args.token:
            parser.error("token cannot be empty")
    if args.poll_interval <= 0:
        parser.error("--poll-interval must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    client = ApiClient(args.api_origin, args.token)
    try:
        result = run_upload(
            client,
            args.source,
            title=args.title or args.source.name,
            description=args.description,
            visibility=args.visibility,
            workers=args.workers,
            wait=not args.no_wait,
            poll_interval=args.poll_interval,
        )
    except KeyboardInterrupt:
        print("upload interrupted", file=sys.stderr)
        return 130
    except UploadError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
