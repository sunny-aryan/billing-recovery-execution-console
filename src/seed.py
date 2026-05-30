import json
from pathlib import Path

from src.database import get_connection


SEED_CASES_PATH = Path("data/seed_cases.json")


def seed_database():
    """
    Load synthetic billing cases into SQLite if the billing_cases table is empty.

    This prevents duplicate seed rows when Streamlit reloads the app.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM billing_cases")
    existing_count = cursor.fetchone()["count"]

    if existing_count > 0:
        conn.close()
        return

    with open(SEED_CASES_PATH, "r", encoding="utf-8") as file:
        seed_cases = json.load(file)

    for case in seed_cases:
        cursor.execute(
            """
            INSERT INTO billing_cases (
                case_id,
                customer_name,
                customer_id,
                invoice_id,
                issue_type,
                amount_cents,
                currency,
                priority,
                status,
                evidence_summary,
                proposed_correction
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case["case_id"],
                case["customer_name"],
                case["customer_id"],
                case["invoice_id"],
                case["issue_type"],
                case["amount_cents"],
                case["currency"],
                case["priority"],
                case["status"],
                case["evidence_summary"],
                case["proposed_correction"],
            ),
        )

    conn.commit()
    conn.close()