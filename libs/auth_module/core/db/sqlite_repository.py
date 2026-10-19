"""
SQLite implementation of the user repository.
"""

import sqlite3
from contextlib import closing
from typing import Any

from .repository import UserRepository


class SQLiteUserRepository(UserRepository):
    """
    A simple SQLite-backed user repository.
    """

    def __init__(self, db_path: str) -> None:
        """
        Initializes the SQLite database connection and ensures tables exist.

        Args:
            db_path (str): The absolute file path to the SQLite database.
        """
        if not db_path:
            raise ValueError('A db_path must be provided to initialize the SQLite repository.')

        self.__db_path = db_path
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a new database connection."""
        conn = sqlite3.connect(self.__db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        """Creates the necessary tables if they don't exist."""
        with closing(self._get_connection()) as conn, conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    password_hash TEXT,
                    verified BOOLEAN NOT NULL DEFAULT 0,
                    name TEXT,
                    oauth_provider TEXT
                )
            ''')

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with closing(self._get_connection()) as conn, conn:
            cursor = conn.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()

            if row:
                return {
                    'email': row['email'],
                    'password': row['password_hash'],
                    'verified': bool(row['verified']),
                    'name': row['name'],
                    'oauth': row['oauth_provider']
                }
            return None

    def create_user(self, email: str, password_hash: str | None, verified: bool, name: str | None = None, oauth_provider: str | None = None) -> None:
        with closing(self._get_connection()) as conn, conn:
            conn.execute('''
                INSERT INTO users (email, password_hash, verified, name, oauth_provider)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, password_hash, verified, name, oauth_provider))

    def update_user_password(self, email: str, new_password_hash: str) -> None:
        with closing(self._get_connection()) as conn, conn:
            conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (new_password_hash, email))

    def update_user_verification(self, email: str, verified: bool) -> None:
        with closing(self._get_connection()) as conn, conn:
            conn.execute('UPDATE users SET verified = ? WHERE email = ?', (verified, email))
