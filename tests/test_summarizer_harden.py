import unittest
from unittest.mock import MagicMock, patch

import requests

from src.summarizer import Summarizer


def _http_error(status, msg="boom"):
    response = MagicMock()
    response.status_code = status
    return requests.exceptions.HTTPError(f"{status} {msg}", response=response)


def _ok_response(text="ok-summary"):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {'choices': [{'message': {'content': text}}]}
    return response


class TestSummarizerHarden(unittest.TestCase):
    def test_truncate_long_transcript(self):
        summarizer = Summarizer(api_key="test-key")
        long_text = "x" * (Summarizer.MAX_TRANSCRIPT_CHARS + 1000)
        with self.assertLogs("src.summarizer", level="WARNING") as logs:
            prompt = summarizer.create_prompt(long_text, style="brief", language="en")
        self.assertIn("truncated", "\n".join(logs.output))
        # 保命：只留前 N 字符，多余的不进 prompt
        self.assertIn("x" * 100, prompt)
        self.assertNotIn("x" * (Summarizer.MAX_TRANSCRIPT_CHARS + 1), prompt)

    def test_no_truncate_short_transcript(self):
        summarizer = Summarizer(api_key="test-key")
        with self.assertNoLogs("src.summarizer", level="WARNING"):
            prompt = summarizer.create_prompt("short hello", style="brief", language="en")
        self.assertIn("short hello", prompt)

    def test_custom_prompt_path_truncates(self):
        summarizer = Summarizer(api_key="test-key")
        long_text = "y" * (Summarizer.MAX_TRANSCRIPT_CHARS + 500)
        with patch.object(summarizer, "_summarize_with_waterfall",
                          return_value=("s", "m")) as mock_wf:
            summarizer.summarize(long_text, custom_prompt="PROMPT")
        sent_prompt = mock_wf.call_args[0][0]
        self.assertIn("PROMPT", sent_prompt)
        self.assertNotIn("y" * (Summarizer.MAX_TRANSCRIPT_CHARS + 1), sent_prompt)

    @patch("src.summarizer.time.sleep", return_value=None)
    @patch("src.summarizer.requests.post")
    def test_400_invalid_model_moves_to_next(self, mock_post, _mock_sleep):
        mock_post.side_effect = [_http_error(400, "No endpoints found for model-a"), _ok_response()]
        summarizer = Summarizer(api_key="test-key")
        summarizer.openrouter_models = ["model-a", "model-b"]
        summary, model = summarizer._summarize_with_waterfall("prompt", 100)
        self.assertEqual(summary, "ok-summary")
        self.assertEqual(model, "model-b")
        self.assertEqual(mock_post.call_count, 2)

    @patch("src.summarizer.time.sleep", return_value=None)
    @patch("src.summarizer.requests.post")
    def test_401_stops_immediately(self, mock_post, _mock_sleep):
        mock_post.side_effect = _http_error(401, "Unauthorized")
        summarizer = Summarizer(api_key="test-key")
        summarizer.openrouter_models = ["model-a", "model-b"]
        with self.assertRaises(RuntimeError) as ctx:
            summarizer._summarize_with_waterfall("prompt", 100)
        self.assertIn("401", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 1)

    @patch("src.summarizer.time.sleep", return_value=None)
    @patch("src.summarizer.requests.post")
    def test_failures_aggregated_in_message(self, mock_post, _mock_sleep):
        mock_post.side_effect = [
            _http_error(400, "invalid model-a"),
            _http_error(500, "server down"),
            _http_error(500, "server down"),
            _http_error(500, "server down"),
        ]
        summarizer = Summarizer(api_key="test-key")
        summarizer.openrouter_models = ["model-a", "model-b"]
        with self.assertRaises(RuntimeError) as ctx:
            summarizer._summarize_with_waterfall("prompt", 100)
        msg = str(ctx.exception)
        self.assertIn("model-a", msg)
        self.assertIn("model-b", msg)
        self.assertIn("400", msg)
        self.assertIn("500", msg)


if __name__ == "__main__":
    unittest.main()
