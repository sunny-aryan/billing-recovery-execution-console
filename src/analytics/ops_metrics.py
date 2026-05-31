"""
Operations metrics for the billing execution workflow.

These queries power the execution operations dashboard. The goal is to help
operators understand execution health, recovery burden, and reconciliation risk.
"""

import pandas as pd

from src.database import get_connection


def get_execution_status_counts():
    """
    Count execution requests by status.

    Returns:
        pandas.DataFrame: status, count
    """
    conn = get_connection()

    query = """
        SELECT
            status,
            COUNT(*) AS count
        FROM execution_requests
        GROUP BY status
        ORDER BY count DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def get_case_status_counts():
    """
    Count billing cases by lifecycle status.

    Returns:
        pandas.DataFrame: status, count
    """
    conn = get_connection()

    query = """
        SELECT
            status,
            COUNT(*) AS count
        FROM billing_cases
        GROUP BY status
        ORDER BY count DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def get_execution_attempt_metrics():
    """
    Calculate aggregate execution attempt metrics.

    Returns:
        dict: Attempt metrics.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM execution_attempts")
    total_attempts = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS transient_failures
        FROM execution_attempts
        WHERE error_type = 'transient'
        """
    )
    transient_failures = cursor.fetchone()["transient_failures"]

    cursor.execute(
        """
        SELECT COUNT(*) AS permanent_failures
        FROM execution_attempts
        WHERE error_type = 'permanent'
        """
    )
    permanent_failures = cursor.fetchone()["permanent_failures"]

    cursor.execute(
        """
        SELECT COUNT(*) AS unknown_failures
        FROM execution_attempts
        WHERE error_type = 'unknown'
        """
    )
    unknown_failures = cursor.fetchone()["unknown_failures"]

    cursor.execute(
        """
        SELECT COUNT(*) AS successful_attempts
        FROM execution_attempts
        WHERE provider_status = 'succeeded'
        """
    )
    successful_attempts = cursor.fetchone()["successful_attempts"]

    conn.close()

    success_rate = 0

    if total_attempts > 0:
        success_rate = successful_attempts / total_attempts

    return {
        "total_attempts": total_attempts,
        "successful_attempts": successful_attempts,
        "transient_failures": transient_failures,
        "permanent_failures": permanent_failures,
        "unknown_failures": unknown_failures,
        "attempt_success_rate": success_rate,
    }


def get_reconciliation_metrics():
    """
    Calculate reconciliation summary metrics.

    Returns:
        dict: Reconciliation metrics.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM reconciliation_runs")
    total_reconciliation_runs = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS matched_success
        FROM reconciliation_runs
        WHERE result = 'matched_success'
        """
    )
    matched_success = cursor.fetchone()["matched_success"]

    cursor.execute(
        """
        SELECT COUNT(*) AS matched_failure
        FROM reconciliation_runs
        WHERE result = 'matched_failure'
        """
    )
    matched_failure = cursor.fetchone()["matched_failure"]

    cursor.execute(
        """
        SELECT COUNT(*) AS mismatches
        FROM reconciliation_runs
        WHERE result IN (
            'provider_succeeded_internal_not_recorded',
            'internal_succeeded_provider_missing',
            'unknown_provider_state'
        )
        """
    )
    mismatches = cursor.fetchone()["mismatches"]

    conn.close()

    return {
        "total_reconciliation_runs": total_reconciliation_runs,
        "matched_success": matched_success,
        "matched_failure": matched_failure,
        "mismatches_or_unknowns": mismatches,
    }


def get_manual_recovery_metrics():
    """
    Calculate manual recovery summary metrics.

    Returns:
        dict: Manual recovery metrics.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM manual_recovery_actions")
    total_manual_recovery_actions = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS manually_resolved
        FROM manual_recovery_actions
        WHERE new_execution_status = 'manually_resolved'
        """
    )
    manually_resolved = cursor.fetchone()["manually_resolved"]

    cursor.execute(
        """
        SELECT COUNT(*) AS cancelled
        FROM manual_recovery_actions
        WHERE new_execution_status = 'cancelled'
        """
    )
    cancelled = cursor.fetchone()["cancelled"]

    conn.close()

    return {
        "total_manual_recovery_actions": total_manual_recovery_actions,
        "manually_resolved": manually_resolved,
        "cancelled": cancelled,
    }


def get_needs_attention_queue():
    """
    Fetch cases/executions that need operational attention.

    Returns:
        pandas.DataFrame: Needs-attention execution records.
    """
    conn = get_connection()

    query = """
        SELECT
            bc.case_id,
            bc.customer_name,
            bc.invoice_id,
            bc.issue_type,
            bc.priority,
            er.execution_request_id,
            er.status AS execution_status,
            er.operation_type,
            er.approved_amount_cents,
            er.currency,
            er.updated_at
        FROM execution_requests er
        JOIN billing_cases bc
            ON er.case_id = bc.case_id
        WHERE er.status IN (
            'failed_transient',
            'failed_permanent',
            'needs_manual_review'
        )
        ORDER BY
            CASE bc.priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            er.updated_at ASC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def get_unreconciled_execution_queue():
    """
    Fetch execution requests that reached terminal execution states but are not reconciled.

    Returns:
        pandas.DataFrame: Unreconciled execution records.
    """
    conn = get_connection()

    query = """
        SELECT
            bc.case_id,
            bc.customer_name,
            er.execution_request_id,
            er.status AS execution_status,
            er.provider_object_id,
            er.updated_at
        FROM execution_requests er
        JOIN billing_cases bc
            ON er.case_id = bc.case_id
        WHERE er.status IN (
            'succeeded',
            'failed_transient',
            'failed_permanent',
            'needs_manual_review'
        )
        AND er.execution_request_id NOT IN (
            SELECT execution_request_id
            FROM reconciliation_runs
            WHERE result IN (
                'matched_success',
                'matched_failure',
                'unknown_provider_state',
                'provider_succeeded_internal_not_recorded',
                'internal_succeeded_provider_missing'
            )
        )
        ORDER BY er.updated_at ASC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df