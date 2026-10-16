# Transaction Webhook Service

A small FastAPI service that acknowledges transaction webhooks immediately and
processes them in a durable SQLite-backed worker.

## Project structure

- `app.py` - application composition and lifecycle management
- `config.py` - environment-backed service settings
- `models.py` - request and response validation models
- `db.py` - SQLite schema and transaction persistence
- `worker.py` - delayed background processing and retry lease handling
- `routes.py` - HTTP endpoints
- `time_utils.py` - UTC timestamp helpers

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

The worker waits 30 seconds before marking each transaction as `PROCESSED`.
Set `PROCESSING_DELAY_SECONDS` to a smaller value when testing. The SQLite file
defaults to `transactions.db`; set `DATABASE_PATH` to place it elsewhere.

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

Submitting the same `transaction_id` more than once is safe: SQLite's primary
key and `INSERT OR IGNORE` ensure that only one processing record is created.
The worker uses a lease so a transaction whose process stops mid-job can be
retried after the lease expires.

## Docker

```bash
docker build -t transaction-webhook-service .
docker run --rm -p 8000:8000 -v transaction-data:/data transaction-webhook-service
```
