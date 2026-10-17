# Transaction Webhook Service

A small FastAPI service that acknowledges transaction webhooks immediately and
processes them in a durable Postgres-backed (Supabase) worker.

Each transaction is marked `PROCESSED` ~30s after it was received.

## Project structure

- `app.py` - application composition and lifecycle management
- `config.py` - environment-backed service settings
- `models.py` - request and response validation models
- `db.py` - Postgres schema and transaction persistence
- `worker.py` - background poller that completes transactions once their delay has elapsed
- `routes.py` - HTTP endpoints
- `time_utils.py` - UTC timestamp helpers

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Supabase > Project Settings > Database > Connection string
export DATABASE_URL='postgresql://postgres:<PASSWORD>@db.<project-ref>.supabase.co:5432/postgres'
uvicorn app:app --reload
```

The worker waits 30 seconds before marking each transaction as `PROCESSED`.
Set `PROCESSING_DELAY_SECONDS` to a smaller value when testing. `DATABASE_URL` is required; the table is created on startup.
If your network is IPv4-only, use the Supabase _pooler_ connection string instead
(the direct `db.*.supabase.co` host is IPv6-only).

## API examples

```bash
curl http://localhost:8000/

curl -X POST http://localhost:8000/v1/webhooks/transactions \
  -H 'content-type: application/json' \
  -d '{
    "transaction_id": "txn_abc123def456",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500,
    "currency": "INR"
  }'

curl http://localhost:8000/v1/transactions/txn_abc123def456
```

## Testing the success criteria

```bash
export PROCESSING_DELAY_SECONDS=3   # use the default 30 for the real thing
uvicorn app:app &
B='{"transaction_id":"t1","source_account":"a","destination_account":"b","amount":5,"currency":"INR"}'
for i in 1 2 3 4 5; do curl -s -X POST localhost:8000/v1/webhooks/transactions -H 'content-type: application/json' -d "$B"; done
curl localhost:8000/v1/transactions/t1   # PROCESSING
sleep 4; curl localhost:8000/v1/transactions/t1   # PROCESSED
```

1. **Single transaction:** status flips to `PROCESSED` after the delay, `processed_at` is set.
2. **Duplicates:** 5 identical POSTs return 202 each, one row exists, processed once.
3. **Performance:** POST only does one Postgres insert and returns 202; processing never blocks requests.
4. **Reliability:** state is persisted before 202 is returned, so a crash or restart loses nothing; pending transactions are completed on the next start. Worker errors are logged and retried on the next poll.

## Technical choices

- **FastAPI + Pydantic:** request validation (positive amount, 3-letter currency, no extra fields) for free.
- **Supabase Postgres:** managed, durable, atomic dedup via `transaction_id` PRIMARY KEY + `ON CONFLICT DO NOTHING`. Timestamps use the DB clock (`now()`), so multiple instances agree.
- **No in-memory queue / per-job sleeping:** the DB row _is_ the queue. One poller completes every row whose `created_at + 30s` has passed, so 1 or 10,000 transactions all finish ~30s after receipt, and restarts need no recovery logic.
- **Scaling:** the due-row `UPDATE` is idempotent, so several instances can run safely.
- A duplicate id with a different payload is accepted (202) and ignored; the first write wins.

## Docker

```bash
docker build -t transaction-webhook-service .
docker run --rm -p 8000:8000 -e DATABASE_URL=... transaction-webhook-service
```

## Cloud deploy

Any container host works (Render, Railway, Fly.io, Cloud Run); set `DATABASE_URL` as a secret. No volume needed.
