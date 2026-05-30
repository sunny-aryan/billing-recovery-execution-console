import pandas as pd

from src.database import get_connection


def get_all_cases():
    """
    Fetch all billing cases from SQLite.

    Returns:
        pandas.DataFrame: All billing cases ordered by priority and creation time.
    """
    conn = get_connection()

    query = """
        SELECT
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
            proposed_correction,
            created_at,
            updated_at
        FROM billing_cases
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            created_at ASC
    """

    cases_df = pd.read_sql_query(query, conn)
    conn.close()

    return cases_df


def get_case_by_id(case_id):
    """
    Fetch one billing case by case_id.

    Args:
        case_id (str): Case identifier, for example CASE-1001.

    Returns:
        dict | None: Case record as a dictionary, or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
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
            proposed_correction,
            created_at,
            updated_at
        FROM billing_cases
        WHERE case_id = ?
        """,
        (case_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def format_amount(amount_cents, currency):
    """
    Format amount from minor units into a display-friendly currency string.

    Example:
        12000, "EUR" -> "EUR 120.00"
    """
    amount = amount_cents / 100
    return f"{currency} {amount:,.2f}"