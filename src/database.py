import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("BILLING_RECOVERY_DB_PATH", "billing_recovery.db"))


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
    Commit 4 added the approvals table.
    Commit 5 added the execution_requests table.
    Commit 6 added the execution_attempts table.
    Commit 8 added the reconciliation_runs table.
    Commit 9 adds the manual_recovery_actions table.
    Commit 10 adds the audit_events table.
    Commit 14 adds the ai_case_briefs table.
    Commit 16 adds the stripe_test_payments table.
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_requests (
            execution_request_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            approval_id TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            approved_amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            provider_object_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES billing_cases(case_id),
            FOREIGN KEY (approval_id) REFERENCES approvals(approval_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_attempts (
            attempt_id TEXT PRIMARY KEY,
            execution_request_id TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            provider TEXT NOT NULL,
            request_payload_json TEXT NOT NULL,
            response_payload_json TEXT NOT NULL,
            provider_status TEXT NOT NULL,
            error_type TEXT,
            error_code TEXT,
            error_message TEXT,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            FOREIGN KEY (execution_request_id) REFERENCES execution_requests(execution_request_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reconciliation_runs (
            reconciliation_id TEXT PRIMARY KEY,
            execution_request_id TEXT NOT NULL,
            internal_status TEXT NOT NULL,
            provider_status TEXT NOT NULL,
            provider_object_id TEXT,
            result TEXT NOT NULL,
            mismatch_reason TEXT,
            action_taken TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (execution_request_id) REFERENCES execution_requests(execution_request_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS manual_recovery_actions (
            manual_recovery_id TEXT PRIMARY KEY,
            execution_request_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            operator_name TEXT NOT NULL,
            rationale TEXT NOT NULL,
            provider_reference_id TEXT,
            previous_execution_status TEXT NOT NULL,
            new_execution_status TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (execution_request_id) REFERENCES execution_requests(execution_request_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_name TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_case_briefs (
            brief_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            dependency_mode TEXT NOT NULL,
            runtime_result TEXT NOT NULL,
            source TEXT NOT NULL,
            summary TEXT NOT NULL,
            customer_impact TEXT NOT NULL,
            missing_evidence_json TEXT NOT NULL,
            risk_notes_json TEXT NOT NULL,
            suggested_reviewer_questions_json TEXT NOT NULL,
            customer_message_draft TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES billing_cases(case_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stripe_test_payments (
            stripe_test_payment_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            dependency_mode TEXT NOT NULL,
            runtime_result TEXT NOT NULL,
            source TEXT NOT NULL,
            payment_intent_id TEXT NOT NULL,
            charge_id TEXT,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES billing_cases(case_id)
        )
        """
    )

    conn.commit()
    conn.close()