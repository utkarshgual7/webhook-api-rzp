from __future__ import annotations

from datetime import timezone

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import Settings
from models import TransactionWebhook
from time_utils import timestamp

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    source_account TEXT NOT NULL,
    destination_account TEXT NOT NULL,
    amount NUMERIC(20, 4) NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PROCESSING', 'PROCESSED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_transactions_work ON transactions(status, created_at);
"""


class TransactionStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        with self.pool.connection() as connection:
            connection.execute(SCHEMA)

    def close(self) -> None:
        self.pool.close()

    def enqueue(self, transaction: TransactionWebhook) -> bool:
        with self.pool.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO transactions (
                    transaction_id, source_account, destination_account,
                    amount, currency, status
                ) VALUES (%s, %s, %s, %s, %s, 'PROCESSING')
                ON CONFLICT (transaction_id) DO NOTHING
                """,
                (
                    transaction.transaction_id,
                    transaction.source_account,
                    transaction.destination_account,
                    transaction.amount,
                    transaction.currency.upper(),
                ),
            )
            return cursor.rowcount == 1

    def process_due(self) -> int:
        """Mark transactions older than the processing delay as PROCESSED."""
        with self.pool.connection() as connection:
            return connection.execute(
                """
                UPDATE transactions SET status = 'PROCESSED', processed_at = now()
                WHERE status = 'PROCESSING'
                  AND created_at <= now() - make_interval(secs => %s)
                """,
                (self.settings.processing_delay_seconds,),
            ).rowcount

    def get(self, transaction_id: str) -> dict | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                "SELECT * FROM transactions WHERE transaction_id = %s",
                (transaction_id,),
            ).fetchone()
        if row is None:
            return None
        for key in ("created_at", "processed_at"):
            if row[key] is not None:
                row[key] = timestamp(row[key].astimezone(timezone.utc))
        return row
