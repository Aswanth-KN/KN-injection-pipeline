from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from app.schemas.events import PipelineEvent
from app.schemas.extraction import ExtractedTicket
from app.services.db_writer import save_extracted_ticket
from app.services.llm_extractor import stream_and_extract

app = FastAPI(title="AI Structured Data Ingestion Pipeline")


class IngestionRequest(BaseModel):
    raw_text: str = Field(min_length=5, description="Raw unstructured email or ticket text")
    model: str | None = Field(default=None, description="Optional Ollama model override")
    base_url: str | None = Field(default=None, description="Optional LLM server URL override")


async def pipeline_event_generator(
    raw_text: str,
    model: str | None = None,
    base_url: str | None = None,
) -> AsyncGenerator[str, None]:
    try:
        async for event in stream_and_extract(raw_text, model=model, base_url=base_url):
            if event.stage == "saving_db" and event.data:
                yield f"data: {event.model_dump_json()}\n\n"
                validated_ticket = ExtractedTicket(**event.data)
                record_id = await save_extracted_ticket(raw_text, validated_ticket)
                completed_event = PipelineEvent(
                    stage="completed",
                    message="Ticket saved to PostgreSQL.",
                    data={"record_id": record_id, "ticket": event.data},
                )
                yield f"data: {completed_event.model_dump_json()}\n\n"
            else:
                yield f"data: {event.model_dump_json()}\n\n"
    except Exception as exc:
        error_event = PipelineEvent(stage="error", message=str(exc))
        yield f"data: {error_event.model_dump_json()}\n\n"


@app.get("/")
async def serve_ui() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.post("/ingest")
async def ingest_ticket(request: IngestionRequest) -> StreamingResponse:
    return StreamingResponse(
        pipeline_event_generator(
            request.raw_text,
            model=request.model,
            base_url=request.base_url,
        ),
        media_type="text/event-stream",
    )