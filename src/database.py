import sqlite3
from pathlib import Path

DB_PATH = Path("billing_recovery.db")


def get_connection():
    """
    Create and return a SQLite database connection.

    If billing_recovery.db does not exist yet, SQLite will create it
    automatically in the project root.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """
    Create required database tables if they do not already exist.
    Commit 1 only creates the billing_cases table.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS billing_cases (
            case_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            proposed_correction TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()