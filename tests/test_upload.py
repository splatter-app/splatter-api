from pathlib import Path
import contextlib
import io
import tempfile
import unittest
from unittest import mock

from load_tool import load_tool


tool = load_tool()


def write_ply(path: Path, payload: bytes = b"abcdefghij") -> None:
    path.write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 3\nend_header\n" + payload)


class FakeClient:
    def __init__(self):
        self.authorize_calls = []
        self.completed = None

    def create(self, path, size, gaussian_count, title, description, visibility):
        self.created = (path, size, gaussian_count, title, description, visibility)
        return {
            "splat": {"publicId": "abc-123-xyz", "status": "uploading"},
            "upload": {"partSizeBytes": 32, "partCount": 3},
        }

    def authorize(self, public_id, part_numbers):
        self.authorize_calls.append(list(part_numbers))
        return {
            "parts": [
                {"partNumber": number, "url": f"https://storage.invalid/{number}"}
                for number in part_numbers
            ]
        }

    def complete(self, public_id, parts):
        self.completed = parts
        return {"splat": {"publicId": public_id, "status": "processing"}}


class UploadTests(unittest.TestCase):
    def test_main_prints_full_splat_link_when_ready(self):
        stdout = io.StringIO()
        with mock.patch.object(
            tool,
            "parse_args",
            return_value=mock.Mock(
                api_origin="https://new.splatter.app/api/v1/",
                token="token",
                source=Path("scan.ply"),
                title=None,
                description=None,
                visibility="unlisted",
                workers=4,
                no_wait=False,
                poll_interval=5.0,
            ),
        ), mock.patch.object(
            tool,
            "run_upload",
            return_value={"publicId": "abc-123-xyz", "status": "ready"},
        ), contextlib.redirect_stdout(stdout):
            exit_code = tool.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                '{"publicId":"abc-123-xyz","status":"ready"}',
                "https://new.splatter.app/s/abc-123-xyz",
            ],
        )

    def test_streams_ranges_and_completes_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.ply"
            write_ply(path)
            client = FakeClient()
            calls = []

            def put_part(url, source, offset, length):
                calls.append((url, offset, length))
                return f'"etag-{offset}"'

            result = tool.run_upload(
                client,
                path,
                title="Scan",
                description=None,
                visibility="unlisted",
                workers=2,
                wait=False,
                poll_interval=1,
                put_part=put_part,
            )
            size = path.stat().st_size
            self.assertEqual(sorted((offset, length) for _, offset, length in calls), [(0, 32), (32, 32), (64, size - 64)])
            self.assertEqual([part["partNumber"] for part in client.completed], [1, 2, 3])
            self.assertEqual(result, {"publicId": "abc-123-xyz", "status": "processing"})

    def test_only_failed_parts_are_reauthorized_and_retried(self):
        client = FakeClient()
        attempts = {}

        def put_part(url, source, offset, length):
            part_number = int(url.rsplit("/", 1)[1])
            attempts[part_number] = attempts.get(part_number, 0) + 1
            if part_number == 2 and attempts[part_number] == 1:
                raise tool.UploadError("temporary failure")
            return f'"etag-{part_number}"'

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.bin"
            path.write_bytes(b"x" * 10)
            parts = tool.upload_parts(client, "abc-123-xyz", path, 10, 4, 3, 3, put_part)

        self.assertEqual(client.authorize_calls, [[1, 2, 3], [2]])
        self.assertEqual(attempts, {1: 1, 2: 2, 3: 1})
        self.assertEqual([part["partNumber"] for part in parts], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
