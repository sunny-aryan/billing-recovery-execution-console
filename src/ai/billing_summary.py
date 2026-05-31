"""
AI billing case brief service.

This service generates an advisory case brief for billing reviewers.

Boundary:
- AI can summarize and structure context.
- AI cannot approve, execute, retry, reconcile, or override deterministic policy.
"""

import json
import os
import uuid

from openai import OpenAI

from src.audit.audit_service import record_audit_event
from src.database import get_connection
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    RUNTIME_RESULT_FALLBACK_USED,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
)


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")


def generate_and_store_case_brief(case, dependency_mode):
    """
    Generate and store an AI billing case brief.

    Args:
        case (dict): Billing case record.
        dependency_mode (str): live or forced_mock.

    Returns:
        dict: Stored AI brief.
    """
    if dependency_mode == DEPENDENCY_MODE_FORCED_MOCK:
        brief_payload = _build_mock_case_brief(case)
        runtime_result = RUNTIME_RESULT_FORCED_MOCK_USED
        source = "forced_mock_ai_brief"
        error_message = None

    elif dependency_mode == DEPENDENCY_MODE_LIVE:
        try:
            brief_payload = _call_openai_for_case_brief(case)
            runtime_result = RUNTIME_RESULT_LIVE_SUCCESS
            source = "openai"
            error_message = None
        except Exception as error:
            brief_payload = _build_fallback_case_brief(case)
            runtime_result = RUNTIME_RESULT_FALLBACK_USED
            source = "deterministic_fallback"
            error_message = str(error)

    else:
        brief_payload = _build_fallback_case_brief(case)
        runtime_result = RUNTIME_RESULT_FALLBACK_USED
        source = "deterministic_fallback"
        error_message = f"Unsupported dependency mode: {dependency_mode}"

    stored_brief = _store_case_brief(
        case=case,
        dependency_mode=dependency_mode,
        runtime_result=runtime_result,
        source=source,
        brief_payload=brief_payload,
        error_message=error_message,
    )

    record_audit_event(
        case_id=case["case_id"],
        entity_type="ai_case_brief",
        entity_id=stored_brief["brief_id"],
        event_type="ai_case_brief_generated",
        actor_type="system",
        actor_name="ai_billing_summary_service",
        details={
            "dependency_mode": dependency_mode,
            "runtime_result": runtime_result,
            "source": source,
            "error_message": error_message,
        },
    )

    return stored_brief


def get_latest_case_brief(case_id):
    """
    Fetch latest AI case brief for a case.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            brief_id,
            case_id,
            dependency_mode,
            runtime_result,
            source,
            summary,
            customer_impact,
            missing_evidence_json,
            risk_notes_json,
            suggested_reviewer_questions_json,
            customer_message_draft,
            error_message,
            created_at
        FROM ai_case_briefs
        WHERE case_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (case_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    brief = dict(row)
    brief["missing_evidence"] = json.loads(brief.pop("missing_evidence_json"))
    brief["risk_notes"] = json.loads(brief.pop("risk_notes_json"))
    brief["suggested_reviewer_questions"] = json.loads(
        brief.pop("suggested_reviewer_questions_json")
    )

    return brief


def _call_openai_for_case_brief(case):
    """
    Call OpenAI to generate a structured billing case brief.

    Returns:
        dict: Case brief payload.
    """
    client = OpenAI()

    prompt = f"""
You are assisting a billing operations reviewer.

Create a concise advisory case brief. Do not approve, reject, or execute anything.

Return valid JSON only with these keys:
- summary: string
- customer_impact: string
- missing_evidence: array of strings
- risk_notes: array of strings
- suggested_reviewer_questions: array of strings
- customer_message_draft: string

Billing case:
case_id: {case["case_id"]}
customer_name: {case["customer_name"]}
customer_id: {case["customer_id"]}
invoice_id: {case["invoice_id"]}
issue_type: {case["issue_type"]}
amount_cents: {case["amount_cents"]}
currency: {case["currency"]}
priority: {case["priority"]}
status: {case["status"]}
evidence_summary: {case["evidence_summary"]}
proposed_correction: {case["proposed_correction"]}
""".strip()

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    raw_text = response.output_text
    parsed = json.loads(raw_text)

    return _normalize_brief_payload(parsed, case)


def _build_mock_case_brief(case):
    """
    Build deterministic mock AI brief for demo mode.
    """
    amount = f"{case['currency']} {case['amount_cents'] / 100:,.2f}"

    return {
        "summary": (
            f"Mock brief: {case['customer_name']} has a billing issue of type "
            f"{case['issue_type']} for invoice {case['invoice_id']}."
        ),
        "customer_impact": (
            f"The customer may have been incorrectly charged {amount}. "
            "Reviewer should confirm the billing evidence before approval."
        ),
        "missing_evidence": [
            "Provider transaction history",
            "Prior correction or credit history",
            "Contract or pricing source used for comparison",
        ],
        "risk_notes": [
            "Mock AI output is advisory only.",
            "Policy evaluation must determine approval eligibility.",
        ],
        "suggested_reviewer_questions": [
            "Has this invoice already received a credit or refund?",
            "Does the proposed correction match the contract or billing evidence?",
        ],
        "customer_message_draft": (
            "We are reviewing your billing correction request and will confirm once "
            "the correction has been verified and approved."
        ),
    }


def _build_fallback_case_brief(case):
    """
    Build deterministic fallback when live OpenAI is unavailable or invalid.
    """
    return {
        "summary": (
            f"Fallback brief: billing case {case['case_id']} concerns "
            f"{case['issue_type']} for customer {case['customer_name']}."
        ),
        "customer_impact": (
            "The customer may experience delayed correction until the billing evidence "
            "is reviewed by an operator."
        ),
        "missing_evidence": [
            "Confirm invoice state",
            "Confirm prior refunds or credits",
            "Confirm approved correction amount",
        ],
        "risk_notes": [
            "Live OpenAI summary was unavailable or invalid.",
            "Use deterministic policy and human review before any approval or execution.",
        ],
        "suggested_reviewer_questions": [
            "Is the correction amount supported by evidence?",
            "Is there any duplicate correction risk?",
        ],
        "customer_message_draft": (
            "We are reviewing the billing issue and will follow up once verification is complete."
        ),
    }


def _normalize_brief_payload(payload, case):
    """
    Normalize OpenAI or fallback payload into the expected shape.
    """
    fallback = _build_fallback_case_brief(case)

    return {
        "summary": str(payload.get("summary") or fallback["summary"]),
        "customer_impact": str(
            payload.get("customer_impact") or fallback["customer_impact"]
        ),
        "missing_evidence": _ensure_string_list(
            payload.get("missing_evidence"),
            fallback["missing_evidence"],
        ),
        "risk_notes": _ensure_string_list(
            payload.get("risk_notes"),
            fallback["risk_notes"],
        ),
        "suggested_reviewer_questions": _ensure_string_list(
            payload.get("suggested_reviewer_questions"),
            fallback["suggested_reviewer_questions"],
        ),
        "customer_message_draft": str(
            payload.get("customer_message_draft")
            or fallback["customer_message_draft"]
        ),
    }


def _ensure_string_list(value, fallback):
    """
    Ensure value is a list of strings.
    """
    if not isinstance(value, list):
        return fallback

    cleaned = [str(item) for item in value if str(item).strip()]

    if not cleaned:
        return fallback

    return cleaned


def _store_case_brief(
    case,
    dependency_mode,
    runtime_result,
    source,
    brief_payload,
    error_message,
):
    """
    Store AI case brief in SQLite.
    """
    brief_id = f"AIB-{uuid.uuid4().hex[:8].upper()}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO ai_case_briefs (
            brief_id,
            case_id,
            dependency_mode,
            runtime_result,
            source,
            summary,
            customer_impact,
            missing_evidence_json,
            risk_notes_json,
            suggested_reviewer_questions_json,
            customer_message_draft,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brief_id,
            case["case_id"],
            dependency_mode,
            runtime_result,
            source,
            brief_payload["summary"],
            brief_payload["customer_impact"],
            json.dumps(brief_payload["missing_evidence"]),
            json.dumps(brief_payload["risk_notes"]),
            json.dumps(brief_payload["suggested_reviewer_questions"]),
            brief_payload["customer_message_draft"],
            error_message,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "brief_id": brief_id,
        "case_id": case["case_id"],
        "dependency_mode": dependency_mode,
        "runtime_result": runtime_result,
        "source": source,
        "summary": brief_payload["summary"],
        "customer_impact": brief_payload["customer_impact"],
        "missing_evidence": brief_payload["missing_evidence"],
        "risk_notes": brief_payload["risk_notes"],
        "suggested_reviewer_questions": brief_payload["suggested_reviewer_questions"],
        "customer_message_draft": brief_payload["customer_message_draft"],
        "error_message": error_message,
    }