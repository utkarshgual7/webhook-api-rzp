from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import load_settings
from db import TransactionStore
from routes import create_router
from worker import TransactionWorker


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

settings = load_settings()
store = TransactionStore(settings.database_path, settings)
worker = TransactionWorker(store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker.start()
    yield
    worker.stop()


app = FastAPI(title="Transaction Webhook Service", lifespan=lifespan)
app.include_router(create_router(store))
