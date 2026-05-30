"""
Centralized audit service.

The audit service records important workflow events across policy evaluation,
approval, execution request creation, provider attempts, retries, reconciliation,
and manual recovery.

Audit events are intentionally stored as append-only records.
"""

import json
import uuid

from src.database import get_connection


def record_audit_event(
    entity_type,
    entity_id,
    event_type,
    actor_type,
    actor_name,
    details,
    case_id=None,
):
    """
    Record a workflow audit event.

    Args:
        entity_type (str): Type of entity, such as case, approval, execution_request.
        entity_id (str): Entity identifier.
        event_type (str): Event type, such as policy_evaluated or approval_created.
        actor_type (str): system, human, provider, or operator.
        actor_name (str): Name of actor or service.
        details (dict): Structured event details.
        case_id (str | None): Optional case identifier.

    Returns:
        dict: Created audit event.
    """
    event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO audit_events (
            event_id,
            case_id,
            entity_type,
            entity_id,
            event_type,
            actor_type,
            actor_name,
            details_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            case_id,
            entity_type,
            entity_id,
            event_type,
            actor_type,
            actor_name,
            json.dumps(details),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "event_id": event_id,
        "case_id": case_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_type": event_type,
        "actor_type": actor_type,
        "actor_name": actor_name,
        "details": details,
    }


def get_audit_events_for_case(case_id):
    """
    Fetch audit events for a case in chronological order.

    Args:
        case_id (str): Billing case identifier.

    Returns:
        list[dict]: Audit events.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            event_id,
            case_id,
            entity_type,
            entity_id,
            event_type,
            actor_type,
            actor_name,
            details_json,
            created_at
        FROM audit_events
        WHERE case_id = ?
        ORDER BY created_at ASC
        """,
        (case_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    events = []

    for row in rows:
        event = dict(row)
        event["details"] = json.loads(event.pop("details_json"))
        events.append(event)

    return events