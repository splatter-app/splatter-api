import contextlib
import io
import os
import sys
import unittest
from unittest import mock

from load_tool import load_tool


tool = load_tool()


class ParseArgsTests(unittest.TestCase):
    def test_prompts_securely_when_token_is_not_configured(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(sys.stdin, "isatty", return_value=True),
            mock.patch.object(tool.getpass, "getpass", return_value="  splatter_v1_test  ") as prompt,
        ):
            args = tool.parse_args(["scan.ply"])

        self.assertEqual(args.token, "splatter_v1_test")
        prompt.assert_called_once_with("Splatter token: ")

    def test_environment_token_does_not_prompt(self):
        with (
            mock.patch.dict(os.environ, {"SPLATTER_TOKEN": "splatter_v1_environment"}, clear=True),
            mock.patch.object(tool.getpass, "getpass") as prompt,
        ):
            args = tool.parse_args(["scan.ply"])

        self.assertEqual(args.token, "splatter_v1_environment")
        prompt.assert_not_called()

    def test_explicit_token_takes_precedence_over_environment(self):
        with mock.patch.dict(
            os.environ, {"SPLATTER_TOKEN": "splatter_v1_environment"}, clear=True
        ):
            args = tool.parse_args(["scan.ply", "--token", "splatter_v1_explicit"])

        self.assertEqual(args.token, "splatter_v1_explicit")

    def test_non_interactive_use_requires_a_configured_token(self):
        stderr = io.StringIO()
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(sys.stdin, "isatty", return_value=False),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            tool.parse_args(["scan.ply"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("set SPLATTER_TOKEN or pass --token", stderr.getvalue())

    def test_empty_prompted_token_is_rejected(self):
        stderr = io.StringIO()
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(sys.stdin, "isatty", return_value=True),
            mock.patch.object(tool.getpass, "getpass", return_value="   "),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            tool.parse_args(["scan.ply"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("token cannot be empty", stderr.getvalue())

    def test_interrupted_prompt_exits_without_a_traceback(self):
        stderr = io.StringIO()
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(sys.stdin, "isatty", return_value=True),
            mock.patch.object(tool.getpass, "getpass", side_effect=KeyboardInterrupt),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            tool.parse_args(["scan.ply"])

        self.assertEqual(raised.exception.code, 130)
        self.assertEqual(stderr.getvalue(), "\ntoken entry interrupted\n")


if __name__ == "__main__":
    unittest.main()
