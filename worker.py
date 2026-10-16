from __future__ import annotations

import logging
import threading

from db import TransactionStore


logger = logging.getLogger(__name__)


class TransactionWorker:
    """Polls for transactions whose delay has elapsed and marks them processed.

    State lives in the DB (created_at), so any number of transactions mature
    concurrently and a restart loses nothing.
    """

    def __init__(self, store: TransactionStore) -> None:
        self.store = store
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="transaction-worker")

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                count = self.store.process_due()
                if count:
                    logger.info("Processed %d transaction(s)", count)
            except Exception:
                logger.exception("Worker iteration failed; retrying")
            self.stop_event.wait(self.store.settings.worker_poll_seconds)
