from fastapi import APIRouter, HTTPException, status

from db import TransactionStore
from models import TransactionResponse, TransactionWebhook
from time_utils import timestamp


def create_router(store: TransactionStore) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def health_check() -> dict[str, str]:
        return {"status": "HEALTHY", "current_time": timestamp()}

    @router.post(
        "/v1/webhooks/transactions",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def receive_transaction(transaction: TransactionWebhook) -> dict[str, str]:
        store.enqueue(transaction)
        return {"status": "ACCEPTED", "transaction_id": transaction.transaction_id}

    @router.get("/v1/transactions/{transaction_id}", response_model=list[TransactionResponse])
    def get_transaction(transaction_id: str) -> list[TransactionResponse]:
        transaction = store.get(transaction_id)
        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found",
            )
        return [
            TransactionResponse(
                transaction_id=transaction["transaction_id"],
                source_account=transaction["source_account"],
                destination_account=transaction["destination_account"],
                amount=transaction["amount"],
                currency=transaction["currency"],
                status=transaction["status"],
                created_at=transaction["created_at"],
                processed_at=transaction["processed_at"],
            )
        ]

    return router
