from __future__ import annotations

import contextlib
import io
import unittest

from scripts.smoke_9router import (
    build_smoke_messages,
    parse_smoke_args,
    parse_smoke_response,
)


class Smoke9RouterTests(unittest.TestCase):
    def test_smoke_prompt_requests_json_compatible_with_router_payload(self) -> None:
        messages = build_smoke_messages()

        self.assertEqual("user", messages[0]["role"])
        self.assertIn("JSON", messages[0]["content"])
        self.assertIn("pong", messages[0]["content"])

    def test_smoke_response_requires_expected_json_status(self) -> None:
        self.assertEqual("pong", parse_smoke_response('{"status":"pong"}'))

        with self.assertRaises(ValueError):
            parse_smoke_response("pong")
        with self.assertRaises(ValueError):
            parse_smoke_response('{"status":"unexpected"}')

    def test_cli_model_argument_overrides_config_model(self) -> None:
        args = parse_smoke_args(["--model", "oc/deepseek-v4-flash-free"])

        self.assertEqual("oc/deepseek-v4-flash-free", args.model)

    def test_cli_rejects_models_outside_gpt55_and_deepseek(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            parse_smoke_args(["--model", "gemini-2.5-flash"])


if __name__ == "__main__":
    unittest.main()
