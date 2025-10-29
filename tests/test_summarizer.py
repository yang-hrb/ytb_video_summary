import unittest
from pathlib import Path
import sys

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.summarizer import Summarizer


class TestSummarizer(unittest.TestCase):
    """测试总结器"""
    
    def test_create_prompt_brief(self):
        """测试简短风格提示词创建"""
        summarizer = Summarizer(api_key="test_key")
        transcript = "这是一个测试转录文本"
        
        prompt = summarizer.create_prompt(transcript, style="brief")
        
        self.assertIn("简洁明了", prompt)
        self.assertIn(transcript, prompt)
        self.assertIn("关键要点", prompt)
    
    def test_create_prompt_detailed(self):
        """测试详细风格提示词创建"""
        summarizer = Summarizer(api_key="test_key")
        transcript = "这是一个测试转录文本"
        
        prompt = summarizer.create_prompt(transcript, style="detailed")
        
        self.assertIn("详细总结", prompt)
        self.assertIn(transcript, prompt)
        self.assertIn("时间轴", prompt)
        self.assertIn("核心见解", prompt)


if __name__ == '__main__':
    unittest.main()
