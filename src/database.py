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

    Commit 1 created the billing_cases table.
    Commit 3 added the policy_evaluations table.
    Commit 4 adds the approvals table.
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS policy_evaluations (
            evaluation_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            outcome TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            requires_manager_approval INTEGER NOT NULL,
            is_blocked INTEGER NOT NULL,
            primary_reason TEXT NOT NULL,
            rules_triggered_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES billing_cases(case_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            approval_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            policy_evaluation_id TEXT NOT NULL,
            approver_name TEXT NOT NULL,
            approver_role TEXT NOT NULL,
            decision TEXT NOT NULL,
            approved_action TEXT NOT NULL,
            approved_amount_cents INTEGER NOT NULL,
            rationale TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES billing_cases(case_id),
            FOREIGN KEY (policy_evaluation_id) REFERENCES policy_evaluations(evaluation_id)
        )
        """
    )

    conn.commit()
    conn.close()