import unittest
import tempfile
from pathlib import Path

from src.database import DatabaseManager
from src.exceptions import DatabaseError


class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()

    def test_create_table(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

        self.assertTrue(self.db.table_exists("test"))
        self.assertFalse(self.db.table_exists("nonexistent"))

    def test_execute_insert(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

        row_id = self.db.execute_insert(
            "INSERT INTO test (name) VALUES (?)",
            ("test_value",)
        )
        self.assertEqual(row_id, 1)

    def test_execute_select(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test (name) VALUES ('item1')")
            conn.execute("INSERT INTO test (name) VALUES ('item2')")

        results = self.db.execute("SELECT * FROM test ORDER BY id")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['name'], 'item1')
        self.assertEqual(results[1]['name'], 'item2')

    def test_execute_one(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test (name) VALUES ('single')")

        result = self.db.execute_one("SELECT * FROM test WHERE name = ?", ("single",))
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'single')

        none_result = self.db.execute_one("SELECT * FROM test WHERE name = ?", ("nonexistent",))
        self.assertIsNone(none_result)

    def test_execute_update(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test (name) VALUES ('old')")

        affected = self.db.execute_update(
            "UPDATE test SET name = ? WHERE name = ?",
            ("new", "old")
        )
        self.assertEqual(affected, 1)

        result = self.db.execute_one("SELECT * FROM test")
        self.assertEqual(result['name'], 'new')

    def test_execute_many(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

        affected = self.db.execute_many(
            "INSERT INTO test (name) VALUES (?)",
            [("item1",), ("item2",), ("item3",)]
        )
        self.assertEqual(affected, 3)

        results = self.db.execute("SELECT * FROM test")
        self.assertEqual(len(results), 3)

    def test_get_table_columns(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")

        columns = self.db.get_table_columns("test")
        self.assertEqual(columns, ["id", "name", "value"])

    def test_transaction_rollback_on_error(self):
        with self.db.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")

        with self.assertRaises(DatabaseError):
            with self.db.get_connection() as conn:
                conn.execute("INSERT INTO test (name) VALUES ('valid')")
                conn.execute("INSERT INTO test (name) VALUES (NULL)")

        results = self.db.execute("SELECT * FROM test")
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
