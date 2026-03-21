"""统一数据库访问层

提供集中的SQLite连接管理、事务处理和错误处理。
所有数据库操作应通过此类进行，以确保一致性和可维护性。
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite数据库管理器

    提供统一的连接管理、事务处理和查询执行。
    使用上下文管理器确保连接正确关闭。
    """

    def __init__(self, db_path: Union[str, Path]):
        """
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path

    @contextmanager
    def get_connection(self, row_factory: bool = False):
        """获取数据库连接的上下文管理器

        Args:
            row_factory: 是否启用Row factory（允许按列名访问）

        Yields:
            sqlite3.Connection: 数据库连接

        Raises:
            DatabaseError: 连接失败时
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            if row_factory:
                conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error("Database error: %s", e)
            raise DatabaseError(f"Database operation failed: {e}", original_error=e)
        finally:
            if conn:
                conn.close()

    def execute(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """执行查询并返回所有结果

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            结果字典列表

        Raises:
            DatabaseError: 查询执行失败时
        """
        with self.get_connection(row_factory=True) as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """执行查询并返回单条结果

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            结果字典，无结果时返回None

        Raises:
            DatabaseError: 查询执行失败时
        """
        results = self.execute(query, params)
        return results[0] if results else None

    def execute_insert(self, query: str, params: Tuple = ()) -> int:
        """执行插入操作并返回新行ID

        Args:
            query: INSERT语句
            params: 插入参数

        Returns:
            新插入行的ID

        Raises:
            DatabaseError: 插入失败时
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid

    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """执行更新操作并返回影响的行数

        Args:
            query: UPDATE语句
            params: 更新参数

        Returns:
            受影响的行数

        Raises:
            DatabaseError: 更新失败时
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """批量执行操作

        Args:
            query: SQL语句
            params_list: 参数列表

        Returns:
            受影响的总行数

        Raises:
            DatabaseError: 执行失败时
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            return cursor.rowcount

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在

        Args:
            table_name: 表名

        Returns:
            表是否存在
        """
        result = self.execute_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return result is not None

    def get_table_columns(self, table_name: str) -> List[str]:
        """获取表的列名列表

        Args:
            table_name: 表名

        Returns:
            列名列表
        """
        result = self.execute(f"PRAGMA table_info({table_name})")
        return [row['name'] for row in result]

    def begin_transaction(self):
        """开始事务（显式）"""
        with self.get_connection() as conn:
            conn.execute("BEGIN")

    def vacuum(self):
        """优化数据库（清理和碎片整理）"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
