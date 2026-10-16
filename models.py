from pydantic import BaseModel, ConfigDict, Field


class TransactionWebhook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=255)
    source_account: str = Field(min_length=1, max_length=255)
    destination_account: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)


class TransactionResponse(TransactionWebhook):
    status: str
    created_at: str
    processed_at: str | None
