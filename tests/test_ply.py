from pathlib import Path
import tempfile
import unittest

from load_tool import load_tool


tool = load_tool()


class InspectPlyTests(unittest.TestCase):
    def test_reads_size_and_vertex_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.ply"
            content = b"ply\nformat binary_little_endian 1.0\nelement vertex 42\nend_header\ndata"
            path.write_bytes(content)
            self.assertEqual(tool.inspect_ply(path), (len(content), 42))

    def test_rejects_missing_vertex_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.ply"
            path.write_bytes(b"ply\nformat ascii 1.0\nend_header\n")
            with self.assertRaisesRegex(tool.UploadError, "vertex count"):
                tool.inspect_ply(path)


if __name__ == "__main__":
    unittest.main()
