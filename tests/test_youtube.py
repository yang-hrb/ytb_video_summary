import unittest
from pathlib import Path
import sys

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.utils import extract_video_id, sanitize_filename, format_duration


class TestYouTubeUtils(unittest.TestCase):
    """测试 YouTube 工具函数"""
    
    def test_extract_video_id(self):
        """测试视频 ID 提取"""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_cases:
            with self.subTest(url=url):
                self.assertEqual(extract_video_id(url), expected_id)
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        test_cases = [
            ("Valid Name.mp4", "Valid Name.mp4"),
            ("Invalid/Name:Test.mp4", "InvalidNameTest.mp4"),
            ("Name  With   Spaces", "Name With Spaces"),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                self.assertEqual(sanitize_filename(input_name), expected)
    
    def test_format_duration(self):
        """测试时长格式化"""
        test_cases = [
            (90, "01:30"),
            (3661, "01:01:01"),
            (45, "00:45"),
        ]
        
        for seconds, expected in test_cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(format_duration(seconds), expected)


if __name__ == '__main__':
    unittest.main()
