from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    processing_delay_seconds: float
    worker_poll_seconds: float


def load_settings() -> Settings:
    processing_delay = float(os.getenv("PROCESSING_DELAY_SECONDS", "30"))
    return Settings(
        database_path=Path(os.getenv("DATABASE_PATH", "transactions.db")),
        processing_delay_seconds=processing_delay,
        worker_poll_seconds=float(os.getenv("WORKER_POLL_SECONDS", "0.25")),
    )
