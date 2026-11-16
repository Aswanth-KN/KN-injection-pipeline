from app.db.models import TicketRecord
from app.db.session import async_session_factory
from app.schemas.extraction import ExtractedTicket


async def save_extracted_ticket(raw_text: str, ticket: ExtractedTicket) -> int:
    async with async_session_factory() as session:
        record = TicketRecord(
            raw_text=raw_text,
            customer_email=ticket.customer_email,
            category=ticket.category,
            urgency=ticket.urgency,
            summary=ticket.summary,
            line_items=[item.model_dump() for item in ticket.line_items],
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id