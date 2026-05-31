from src.ai.billing_summary import (
    generate_and_store_case_brief,
    get_latest_case_brief,
)
from src.cases.case_service import get_case_by_id
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    RUNTIME_RESULT_FALLBACK_USED,
    RUNTIME_RESULT_FORCED_MOCK_USED,
)


def test_forced_mock_ai_case_brief_is_stored(test_db):
    case = get_case_by_id("CASE-1003")

    brief = generate_and_store_case_brief(
        case=case,
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    assert brief["case_id"] == "CASE-1003"
    assert brief["runtime_result"] == RUNTIME_RESULT_FORCED_MOCK_USED
    assert brief["source"] == "forced_mock_ai_brief"
    assert brief["summary"]


def test_latest_ai_case_brief_can_be_fetched(test_db):
    case = get_case_by_id("CASE-1003")

    generate_and_store_case_brief(
        case=case,
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    latest = get_latest_case_brief("CASE-1003")

    assert latest is not None
    assert latest["case_id"] == "CASE-1003"
    assert latest["missing_evidence"]


def test_live_mode_falls_back_when_openai_call_fails(test_db, monkeypatch):
    case = get_case_by_id("CASE-1003")

    def mock_openai_failure(_case):
        raise RuntimeError("Simulated OpenAI failure")

    monkeypatch.setattr(
        "src.ai.billing_summary._call_openai_for_case_brief",
        mock_openai_failure,
    )

    brief = generate_and_store_case_brief(
        case=case,
        dependency_mode=DEPENDENCY_MODE_LIVE,
    )

    assert brief["runtime_result"] == RUNTIME_RESULT_FALLBACK_USED
    assert brief["source"] == "deterministic_fallback"
    assert "Simulated OpenAI failure" in brief["error_message"]