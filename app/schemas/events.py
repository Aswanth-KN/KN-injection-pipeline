from typing import Any, Literal
from pydantic import BaseModel


class PipelineEvent(BaseModel):
    stage: Literal["validating", "streaming_tokens", "saving_db", "completed", "error"]
    message: str
    data: dict[str, Any] | None = None
