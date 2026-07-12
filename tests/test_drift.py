from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.drift import evaluate_drift
from app.schemas.drift import DailyEntry

client = TestClient(app)
HEADERS = {"X-API-Key": "dev-local-key"}


def _entry(days_before_ref: int, ref: date, mood: str | None, completed: int, total: int, journal_len: int) -> DailyEntry:
    return DailyEntry(
        date=ref - timedelta(days=days_before_ref),
        mood=mood,
        tasks_completed=completed,
        tasks_total=total,
        journal_length=journal_len,
    )


def test_insufficient_data_with_few_entries():
    ref = date(2026, 7, 12)
    entries = [_entry(i, ref, "Grounded", 2, 3, 200) for i in range(3)]
    result = evaluate_drift(entries, reference_date=ref)
    assert result.status == "insufficient-data"


def test_steady_when_recent_matches_baseline():
    ref = date(2026, 7, 12)
    # 25 days of consistent "Grounded" mood, full task completion, steady journaling
    entries = [_entry(i, ref, "Grounded", 3, 3, 200) for i in range(25)]
    result = evaluate_drift(entries, reference_date=ref)
    assert result.status == "steady"


def test_check_in_when_multiple_signals_dip_together():
    ref = date(2026, 7, 12)
    # Solid baseline for the older 17-24 day window
    baseline_entries = [_entry(i, ref, "Thriving", 3, 3, 300) for i in range(4, 25)]
    # Sustained recent decline across mood, completion, and journaling
    recent_entries = [_entry(i, ref, "Blocked", 0, 3, 20) for i in range(0, 4)]
    result = evaluate_drift(baseline_entries + recent_entries, reference_date=ref)
    assert result.status == "check-in"
    assert result.dipping_count >= 2


def test_drift_endpoint_requires_api_key():
    response = client.post("/drift/evaluate", json={"entries": []})
    assert response.status_code == 401


def test_drift_endpoint_with_valid_key():
    ref = "2026-07-12"
    entries = [
        {
            "date": ref,
            "mood": "Grounded",
            "tasks_completed": 2,
            "tasks_total": 3,
            "journal_length": 150,
        }
    ]
    response = client.post(
        "/drift/evaluate",
        json={"entries": entries, "reference_date": ref},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient-data"
