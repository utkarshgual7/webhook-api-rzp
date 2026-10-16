from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

from config import Settings
from models import TransactionWebhook
from time_utils import timestamp, utc_now


class TransactionStore:
    def __init__(self, path: Path, settings: Settings) -> None:
        self.path = path
        self.settings = settings
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    source_account TEXT NOT NULL,
                    destination_account TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('PROCESSING', 'PROCESSED')),
                    created_at TEXT NOT NULL,
                    processed_at TEXT,
                    lease_until TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_work "
                "ON transactions(status, lease_until)"
            )

    def enqueue(self, transaction: TransactionWebhook) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO transactions (
                    transaction_id, source_account, destination_account, amount,
                    currency, status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'PROCESSING', ?)
                """,
                (
                    transaction.transaction_id,
                    transaction.source_account,
                    transaction.destination_account,
                    transaction.amount,
                    transaction.currency.upper(),
                    timestamp(),
                ),
            )
            return cursor.rowcount == 1

    def claim_next(self) -> sqlite3.Row | None:
        now = utc_now()
        lease = timestamp(now + timedelta(seconds=self.settings.processing_lease_seconds))
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM transactions
                WHERE status = 'PROCESSING'
                  AND (lease_until IS NULL OR lease_until <= ?)
                ORDER BY created_at
                LIMIT 1
                """,
                (timestamp(now),),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            connection.execute(
                "UPDATE transactions SET lease_until = ? WHERE transaction_id = ?",
                (lease, row["transaction_id"]),
            )
            connection.commit()
            return row

    def mark_processed(self, transaction_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE transactions
                SET status = 'PROCESSED', processed_at = ?, lease_until = NULL
                WHERE transaction_id = ? AND status = 'PROCESSING'
                """,
                (timestamp(), transaction_id),
            )

    def get(self, transaction_id: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM transactions WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
