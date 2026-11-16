from typing import Literal
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = Field(description="Clean name of the product or service")
    quantity: float = Field(gt=0, description="Quantity ordered. Default to 1 if not stated.")
    unit_price: float = Field(ge=0, description="Price per unit in USD")


class ExtractedTicket(BaseModel):
    customer_email: str | None = Field(
        default=None,
        description="Sender email address if found in the text, otherwise null",
    )
    category: Literal["billing", "bug_report", "feature_request", "cancellation"] = Field(
        description="Main topic of the message"
    )
    urgency: Literal["low", "medium", "high", "critical"] = Field(
        description="Urgency level based on tone, deadlines, or money lost"
    )
    summary: str = Field(
        max_length=200,
        description="One short sentence that summarizes the issue",
    )
    line_items: list[LineItem] = Field(
        default_factory=list,
        description="List of invoice or purchase items mentioned in the text",
    )
