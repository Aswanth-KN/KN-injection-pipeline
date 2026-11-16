import json
from pathlib import Path
import pytest

from app.schemas.extraction import ExtractedTicket
from app.services.llm_extractor import stream_and_extract


FIXTURES_PATH = Path(__file__).parent / "fixtures" / "eval_cases.json"
EVAL_CASES = json.loads(FIXTURES_PATH.read_text())


async def run_extraction(raw_text: str) -> ExtractedTicket:
    extracted_payload = None
    async for event in stream_and_extract(raw_text):
        if event.stage == "saving_db" and event.data:
            extracted_payload = event.data
    assert extracted_payload is not None, "LLM failed to produce a validated schema"
    return ExtractedTicket(**extracted_payload)


@pytest.mark.asyncio
async def test_llm_extraction_eval_suite() -> None:
    total_checks = 0
    passed_checks = 0
    failures: list[str] = []

    for case in EVAL_CASES:
        ticket = await run_extraction(case["raw_text"])
        exp = case["expected"]

        # Check 1: Customer Email (No hallucination on null)
        total_checks += 1
        if ticket.customer_email == exp["customer_email"]:
            passed_checks += 1
        else:
            failures.append(
                f"[{case['id']}] email mismatch: got {ticket.customer_email!r}, expected {exp['customer_email']!r}"
            )

        # Check 2: Category Classification
        total_checks += 1
        if ticket.category == exp["category"]:
            passed_checks += 1
        else:
            failures.append(
                f"[{case['id']}] category mismatch: got {ticket.category!r}, expected {exp['category']!r}"
            )

        # Check 3: Urgency Calibration (Allow high/critical equivalence on urgent incidents)
        total_checks += 1
        urgent_tiers = {"high", "critical"}
        urgency_ok = (
            ticket.urgency in urgent_tiers
            if exp["urgency"] in urgent_tiers
            else ticket.urgency == exp["urgency"]
        )
        if urgency_ok:
            passed_checks += 1
        else:
            failures.append(
                f"[{case['id']}] urgency mismatch: got {ticket.urgency!r}, expected {exp['urgency']!r}"
            )

        # Check 4: Line Item Count & Total Math
        total_checks += 1
        extracted_total = sum(i.quantity * i.unit_price for i in ticket.line_items)
        if (
            len(ticket.line_items) >= exp["min_line_items"]
            and abs(extracted_total - exp["expected_total_amount"]) < 0.01
        ):
            passed_checks += 1
        else:
            failures.append(
                f"[{case['id']}] line_items mismatch: got {ticket.line_items} (total={extracted_total}), "
                f"expected total={exp['expected_total_amount']}"
            )

    accuracy = (passed_checks / total_checks) * 100
    print(f"\nEval Score: {passed_checks}/{total_checks} checks passed ({accuracy:.1f}%)")
    for f in failures:
        print("  FAIL ->", f)

    assert accuracy >= 85.0, f"Eval accuracy {accuracy:.1f}% dropped below 85% production threshold!"