import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from fastapi import HTTPException

import auth


class RefreshTokenTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = auth.REFRESH_TOKEN_DB_PATH
        auth.REFRESH_TOKEN_DB_PATH = str(
            Path(self.temp_directory.name) / "refresh_tokens.db"
        )

    def tearDown(self):
        auth.REFRESH_TOKEN_DB_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_refresh_token_is_stored_on_disk_and_can_be_rotated(self):
        refresh_token = auth.create_refresh_token("test-user")

        with sqlite3.connect(auth.REFRESH_TOKEN_DB_PATH) as connection:
            stored_tokens = connection.execute(
                "SELECT COUNT(*) FROM refresh_tokens WHERE subject = ?",
                ("test-user",),
            ).fetchone()[0]

        self.assertEqual(stored_tokens, 1)

        response = auth.refresh(auth.RefreshRequest(refresh_token=refresh_token))
        self.assertTrue(response.access_token)
        self.assertTrue(response.refresh_token)
        self.assertNotEqual(response.refresh_token, refresh_token)

    def test_rotated_refresh_token_cannot_be_reused(self):
        refresh_token = auth.create_refresh_token("test-user")
        auth.refresh(auth.RefreshRequest(refresh_token=refresh_token))

        with self.assertRaises(HTTPException) as raised:
            auth.refresh(auth.RefreshRequest(refresh_token=refresh_token))

        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
