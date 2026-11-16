from collections.abc import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings
from app.schemas.events import PipelineEvent
from app.schemas.extraction import ExtractedTicket

client = AsyncOpenAI(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)


# sets strict rules to models.
SYSTEM_PROMPT = """
You are a deterministic data extraction engine. Extract structured ticket and invoice data 
from the user's raw text. Never invent missing emails or prices. If a field is absent, 
return null or an empty list as permitted by the schema.

Classification Priority Rules:
- If the message reports an outage, crash, 500 error, or broken functionality, classify category as 'bug_report' even if financial loss is mentioned.
- Classify as 'billing' only when the primary issue is an invoice, overcharge, refund request, or payment failure.
- Classify as 'cancellation' when the user explicitly asks to cancel or terminate a subscription/account.
- Classify as 'feature_request' when asking for new capabilities.
"""


async def stream_and_extract(
    raw_text: str,
    model: str | None = None,
    base_url: str | None = None,
) -> AsyncGenerator[PipelineEvent, None]:
    active_model = model or settings.llm_model
    custom_client = (
        AsyncOpenAI(base_url=base_url, api_key=settings.llm_api_key)
        if base_url
        else None
    )
    active_client = custom_client or client

    try:
        yield PipelineEvent(
            stage="validating",
            message=f"Loading {active_model} & evaluating prompt...",
        )

        async with active_client.beta.chat.completions.stream(
            model=active_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            response_format=ExtractedTicket,
            temperature=0.0,
        ) as stream:
            async for event in stream:
                if event.type == "content.delta":
                    yield PipelineEvent(
                        stage="streaming_tokens",
                        message="delta",
                        data={"chunk": event.delta},
                    )

            final_completion = await stream.get_final_completion()
            parsed_ticket: ExtractedTicket | None = final_completion.choices[0].message.parsed

            if not parsed_ticket:
                yield PipelineEvent(
                    stage="error",
                    message="Model refused or failed schema validation.",
                )
                return

            yield PipelineEvent(
                stage="saving_db",
                message="Schema validated. Ready to save.",
                data=parsed_ticket.model_dump(),
            )
    finally:
        if custom_client:
            await custom_client.close()
