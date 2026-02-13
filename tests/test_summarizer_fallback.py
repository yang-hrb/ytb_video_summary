import unittest
from unittest.mock import MagicMock, patch

import requests

from src.summarizer import Summarizer


class TestSummarizerFallback(unittest.TestCase):
    def test_clean_srt_content(self):
        raw = """1
00:00:01,000 --> 00:00:02,000
Hello

2
00:00:03,000 --> 00:00:04,000
World
"""
        self.assertEqual(Summarizer.clean_srt_content(raw), "Hello World")

    @patch('src.summarizer.time.sleep', return_value=None)
    @patch('src.summarizer.requests.post')
    def test_openrouter_waterfall_switches_model_on_429(self, mock_post, _mock_sleep):
        fail_response = MagicMock()
        fail_response.status_code = 429
        http_error = requests.exceptions.HTTPError(response=fail_response)

        ok_response = MagicMock()
        ok_response.raise_for_status.return_value = None
        ok_response.json.return_value = {
            'choices': [{'message': {'content': 'ok-summary'}}]
        }

        mock_post.side_effect = [http_error, ok_response]

        summarizer = Summarizer(api_key='test-key')
        summarizer.openrouter_models = ['model-a', 'model-b']
        summary = summarizer._summarize_with_waterfall('prompt', 100)

        self.assertEqual(summary, 'ok-summary')
        self.assertEqual(mock_post.call_count, 2)


if __name__ == '__main__':
    unittest.main()
