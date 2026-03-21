import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from src.prompt_selector import PromptSelector

class TestPromptSelector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "config"
        self.config_dir.mkdir(parents=True)
        self.prompts_dir = self.config_dir / "prompt_types"
        self.prompts_dir.mkdir(parents=True)
        
        # Create CSV
        csv_path = self.config_dir / "prompt_profile_map.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("uploader,prompt_type\nTechLead,talk\n")
            
        # Create prompts
        default_prompt = self.prompts_dir / "default.txt"
        with open(default_prompt, "w", encoding="utf-8") as f:
            f.write("Default prompt")
            
        talk_prompt = self.prompts_dir / "talk.txt"
        with open(talk_prompt, "w", encoding="utf-8") as f:
            f.write("Talk prompt 1\n---\nTalk prompt 2")
            
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_select_for_uploader_match(self):
        selector = PromptSelector(self.config_dir)
        res = selector.select_for_uploader("TechLead")
        self.assertEqual(res['prompt_type'], "talk")
        self.assertEqual(res['prompt_source'], "csv")
        self.assertIn("Talk prompt", res['prompt_text'])
        
    def test_select_for_uploader_fallback_default(self):
        selector = PromptSelector(self.config_dir)
        res = selector.select_for_uploader("UnknownUploader")
        self.assertEqual(res['prompt_type'], "default")
        self.assertEqual(res['prompt_source'], "default")
        self.assertEqual(res['prompt_text'], "Default prompt")
        
    def test_select_for_uploader_no_files(self):
        selector = PromptSelector(Path("/nonexistent_dir"))
        res = selector.select_for_uploader("TechLead")
        self.assertEqual(res['prompt_type'], "default")
        self.assertEqual(res['prompt_source'], "builtin")
        self.assertIsNone(res['prompt_text'])

if __name__ == '__main__':
    unittest.main()
