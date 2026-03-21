import unittest
from src.batch_processor import BatchProcessor, BatchResult


class TestBatchProcessor(unittest.TestCase):

    def test_process_success(self):
        def double(x: int, **kwargs) -> int:
            return x * 2

        processor = BatchProcessor(processor_fn=double, label="Double")
        result = processor.process([1, 2, 3])

        self.assertEqual(result.total, 3)
        self.assertEqual(result.succeeded, 3)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.results, [2, 4, 6])
        self.assertTrue(result.success)

    def test_process_with_failures(self):
        def safe_divide(x: int, divisor: int = 1, **kwargs) -> float:
            return x / divisor

        processor = BatchProcessor(processor_fn=safe_divide, label="Divide")
        result = processor.process([10, 20, 30], divisor=0)

        self.assertEqual(result.total, 3)
        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 3)
        self.assertFalse(result.success)
        self.assertEqual(len(result.failures), 3)

    def test_process_mixed_results(self):
        def conditional_fail(x: int, **kwargs) -> int:
            if x % 2 == 0:
                raise ValueError(f"Even number: {x}")
            return x

        processor = BatchProcessor(processor_fn=conditional_fail, label="Conditional")
        result = processor.process([1, 2, 3, 4, 5])

        self.assertEqual(result.total, 5)
        self.assertEqual(result.succeeded, 3)
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.results[0], 1)
        self.assertIn('error', result.results[1])

    def test_process_empty_list(self):
        def identity(x: int, **kwargs) -> int:
            return x

        processor = BatchProcessor(processor_fn=identity, label="Empty")
        result = processor.process([])

        self.assertEqual(result.total, 0)
        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 0)
        self.assertTrue(result.success)

    def test_custom_log_item_name(self):
        def process_url(url: str, **kwargs) -> str:
            return url.upper()

        def url_formatter(idx: int, url: str) -> str:
            return f"URL {idx}: {url[:20]}..."

        processor = BatchProcessor(
            processor_fn=process_url,
            label="URLs",
            log_item_name=url_formatter,
        )
        result = processor.process(["https://example.com/very-long-url-path"])

        self.assertEqual(result.total, 1)
        self.assertEqual(result.succeeded, 1)
        self.assertEqual(result.results[0], "HTTPS://EXAMPLE.COM/VERY-LONG-URL-PATH")


class TestBatchResult(unittest.TestCase):

    def test_batch_result_dataclass(self):
        result = BatchResult(
            total=10,
            succeeded=8,
            failed=2,
            results=[1, 2, 3],
            failures=[(1, "item1", "error1"), (2, "item2", "error2")],
            success=False,
        )

        self.assertEqual(result.total, 10)
        self.assertEqual(result.succeeded, 8)
        self.assertEqual(result.failed, 2)
        self.assertFalse(result.success)


if __name__ == '__main__':
    unittest.main()
