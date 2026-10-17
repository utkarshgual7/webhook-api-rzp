from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    processing_delay_seconds: float
    worker_poll_seconds: float


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        processing_delay_seconds=float(os.getenv("PROCESSING_DELAY_SECONDS", "30")),
        worker_poll_seconds=float(os.getenv("WORKER_POLL_SECONDS", "0.25")),
    )
