import unittest
from pathlib import Path
import sys

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.utils import format_timestamp


class TestTranscriberUtils(unittest.TestCase):
    """测试转录工具函数"""
    
    def test_format_timestamp(self):
        """测试 SRT 时间戳格式化"""
        test_cases = [
            (0, "00:00:00,000"),
            (1.5, "00:00:01,500"),
            (65.123, "00:01:05,123"),
            (3661.456, "01:01:01,456"),
        ]
        
        for seconds, expected in test_cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(format_timestamp(seconds), expected)


if __name__ == '__main__':
    unittest.main()
