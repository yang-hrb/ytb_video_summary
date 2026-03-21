"""通用批处理器模块

提供统一的批处理接口，消除重复的批处理循环模式。
"""

import logging
from typing import Callable, List, TypeVar, Generic, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchResult(Generic[T, R]):
    total: int
    succeeded: int
    failed: int
    results: List[R]
    failures: List[tuple]
    success: bool = True


class BatchProcessor(Generic[T, R]):

    def __init__(
        self,
        processor_fn: Callable[[T, Any], R],
        label: str = "Batch",
        log_item_name: Callable[[int, T], str] = None,
    ):
        self.processor_fn = processor_fn
        self.label = label
        self.log_item_name = log_item_name or (lambda idx, item: f"[{idx}]")

    def process(
        self,
        items: List[T],
        **kwargs,
    ) -> BatchResult[T, R]:
        results: List[R] = []
        failures: List[tuple] = []

        for idx, item in enumerate(items, 1):
            item_name = self.log_item_name(idx, item)
            logger.info("=" * 60)
            logger.info("%s %d/%d: %s", self.label, idx, len(items), item_name)
            logger.info("=" * 60)

            try:
                result = self.processor_fn(item, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error("Failed: %s", e)
                logger.debug("Details", exc_info=True)
                failures.append((idx, item, str(e)))
                results.append({'error': str(e), 'item': item})

        self._log_summary(len(items), len(items) - len(failures), len(failures), failures)

        return BatchResult(
            total=len(items),
            succeeded=len(items) - len(failures),
            failed=len(failures),
            results=results,
            failures=failures,
            success=len(failures) == 0,
        )

    def _log_summary(self, total: int, success: int, failed: int, failed_items: List[tuple]) -> None:
        logger.info("=" * 60)
        logger.info("%s processing complete", self.label)
        logger.info("=" * 60)
        logger.info("Total: %d | Success: %d | Failed: %d", total, success, failed)
        if failed_items:
            logger.warning("Failed items:")
            for item in failed_items:
                if len(item) == 3:
                    logger.warning("  [%s] %s", item[0], item[2])
