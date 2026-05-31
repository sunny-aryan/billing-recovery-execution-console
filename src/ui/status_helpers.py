"""
UI helpers for status labels and workflow guidance.

These helpers keep workflow state readable in the Streamlit UI without changing
the underlying execution logic.
"""


def format_status_label(status):
    """
    Convert snake_case status values into readable labels.
    """
    if status is None:
        return "Unknown"

    return str(status).replace("_", " ").title()


def get_dependency_result_message(runtime_result):
    """
    Return a readable dependency runtime message.
    """
    if runtime_result == "live_success":
        return "Live API response used"

    if runtime_result == "forced_mock_used":
        return "Forced mock response used"

    if runtime_result == "fallback_used":
        return "Fallback used after live call failed"

    if runtime_result == "failed_safely":
        return "Failed safely"

    return "Unknown dependency result"


def get_execution_status_guidance(status):
    """
    Explain what the operator should do next for an execution status.
    """
    if status is None:
        return "Create an execution request after approval."

    if status == "execution_pending":
        return "Execute the request with the mock provider or Stripe test mode."

    if status == "processing":
        return "Execution is in progress. Refresh if needed."

    if status == "retrying":
        return "Retry is in progress. Refresh if needed."

    if status == "succeeded":
        return "Run reconciliation to verify provider source of truth."

    if status == "failed_transient":
        return "Retry is allowed under deterministic retry policy."

    if status == "failed_permanent":
        return "Do not retry automatically. Reconcile or route to manual recovery."

    if status == "needs_manual_review":
        return "Run reconciliation if needed, then use manual recovery."

    if status == "reconciled":
        return "Execution has been verified against provider source of truth."

    if status == "manually_resolved":
        return "Execution was resolved through manual recovery."

    if status == "cancelled":
        return "Execution was cancelled and should not continue."

    if status == "under_review":
        return "Case has been reopened for investigation."

    return "Review execution history and determine next action."


def get_case_workflow_stage(case_status, execution_status=None):
    """
    Return a high-level workflow stage for the case detail page.
    """
    if execution_status == "reconciled":
        return "Reconciled"

    if execution_status == "manually_resolved":
        return "Manually Resolved"

    if execution_status == "cancelled":
        return "Cancelled"

    if execution_status in [
        "succeeded",
        "failed_transient",
        "failed_permanent",
        "needs_manual_review",
    ]:
        return "Post-Execution Review"

    if execution_status == "execution_pending":
        return "Ready for Provider Execution"

    if case_status == "approved":
        return "Approved"

    if case_status in ["eligible_for_approval", "requires_manager_approval"]:
        return "Policy Evaluated"

    if case_status == "blocked":
        return "Blocked by Policy"

    if case_status == "needs_more_review":
        return "Needs Review"

    return "Case Review"