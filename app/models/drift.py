"""
Model 1: Change-point / drift detection.

Compares a user's recent behavior (mood, task completion, journaling) against
their own rolling baseline to flag a genuine, sustained dip — not ordinary
day-to-day variation. Uses a CUSUM-style cumulative deviation statistic:
simple, explainable, and needs no training data, which makes it a solid v1
before any heavier changepoint method is justified.

Design principles (carried over from the JS prototype):
- Compare each user only to their OWN history, never to other users.
- Require multiple signals to dip together before flagging anything to the
  user, to avoid false alarms from a single ordinary bad day.
- Stay silent until there's enough baseline history to know what's "normal"
  for this specific person.
"""
from __future__ import annotations

from datetime import date, datetime
from statistics import mean, pstdev

from app.schemas.drift import DailyEntry, DriftResult, SignalResult

MOOD_SCALE = {"Thriving": 4, "Grounded": 3, "Low": 2, "Blocked": 1}

DEFAULT_BASELINE_WINDOW_DAYS = 21
DEFAULT_RECENT_WINDOW_DAYS = 4
DEFAULT_MIN_BASELINE_POINTS = 10
DEFAULT_CUSUM_THRESHOLD = 4.0  # cumulative deviation (in std devs) to trip
DEFAULT_COMPLETION_DROP_THRESHOLD = 0.25
DEFAULT_JOURNAL_DROP_THRESHOLD = 0.5
DEFAULT_SIGNALS_REQUIRED = 2


def _days_ago(entry_date: date, reference: date) -> int:
    return (reference - entry_date).days


def _split_windows(
    entries: list[DailyEntry],
    reference: date,
    baseline_window_days: int,
    recent_window_days: int,
) -> tuple[list[DailyEntry], list[DailyEntry]]:
    ordered = sorted(entries, key=lambda e: e.date)
    recent = [e for e in ordered if _days_ago(e.date, reference) < recent_window_days]
    baseline = [
        e
        for e in ordered
        if recent_window_days <= _days_ago(e.date, reference) < baseline_window_days
    ]
    return baseline, recent


def _cusum_signal(values: list[float]) -> float:
    """
    Cumulative sum of standardized deviations from the running mean.
    A large negative CUSUM means a sustained run of below-average values —
    exactly the "quiet, creeping decline" pattern a single-day z-score misses.
    """
    if len(values) < 2:
        return 0.0
    m = mean(values)
    sd = pstdev(values) or 0.5  # floor to avoid division by ~0
    cusum = 0.0
    min_cusum = 0.0
    for v in values:
        cusum = min(0.0, cusum + (v - m) / sd)
        min_cusum = min(min_cusum, cusum)
    return min_cusum


def _evaluate_mood(
    baseline: list[DailyEntry], recent: list[DailyEntry], min_baseline_points: int, cusum_threshold: float
) -> SignalResult:
    baseline_scores = [MOOD_SCALE[e.mood] for e in baseline if e.mood]
    recent_scores = [MOOD_SCALE[e.mood] for e in recent if e.mood]

    if len(baseline_scores) < min_baseline_points or not recent_scores:
        return SignalResult(available=False)

    combined = baseline_scores + recent_scores
    cusum = _cusum_signal(combined)

    return SignalResult(
        available=True,
        baseline_avg=round(mean(baseline_scores), 2),
        recent_avg=round(mean(recent_scores), 2),
        statistic=round(cusum, 2),
        dipping=cusum <= -cusum_threshold,
    )


def _evaluate_completion(
    baseline: list[DailyEntry], recent: list[DailyEntry], min_baseline_points: int, drop_threshold: float
) -> SignalResult:
    def rate(entries: list[DailyEntry]) -> float | None:
        with_tasks = [e for e in entries if (e.tasks_total or 0) > 0]
        if not with_tasks:
            return None
        done = sum(e.tasks_completed or 0 for e in with_tasks)
        total = sum(e.tasks_total or 0 for e in with_tasks)
        return done / total if total else None

    baseline_rate = rate(baseline)
    recent_rate = rate(recent)

    if baseline_rate is None or recent_rate is None or len(baseline) < min_baseline_points:
        return SignalResult(available=False)

    drop = baseline_rate - recent_rate
    return SignalResult(
        available=True,
        baseline_avg=round(baseline_rate, 2),
        recent_avg=round(recent_rate, 2),
        statistic=round(drop, 2),
        dipping=drop >= drop_threshold,
    )


def _evaluate_journal(
    baseline: list[DailyEntry], recent: list[DailyEntry], min_baseline_points: int, drop_threshold: float
) -> SignalResult:
    baseline_lengths = [e.journal_length or 0 for e in baseline]
    recent_lengths = [e.journal_length or 0 for e in recent]

    if len(baseline_lengths) < min_baseline_points or not recent_lengths:
        return SignalResult(available=False)

    baseline_avg = mean(baseline_lengths)
    if not baseline_avg:
        return SignalResult(available=False)

    recent_avg = mean(recent_lengths)
    relative_drop = (baseline_avg - recent_avg) / baseline_avg

    return SignalResult(
        available=True,
        baseline_avg=round(baseline_avg, 1),
        recent_avg=round(recent_avg, 1),
        statistic=round(relative_drop, 2),
        dipping=relative_drop >= drop_threshold,
    )


def evaluate_drift(
    entries: list[DailyEntry],
    reference_date: date | None = None,
    baseline_window_days: int = DEFAULT_BASELINE_WINDOW_DAYS,
    recent_window_days: int = DEFAULT_RECENT_WINDOW_DAYS,
    min_baseline_points: int = DEFAULT_MIN_BASELINE_POINTS,
    cusum_threshold: float = DEFAULT_CUSUM_THRESHOLD,
    completion_drop_threshold: float = DEFAULT_COMPLETION_DROP_THRESHOLD,
    journal_drop_threshold: float = DEFAULT_JOURNAL_DROP_THRESHOLD,
    signals_required: int = DEFAULT_SIGNALS_REQUIRED,
) -> DriftResult:
    reference = reference_date or datetime.utcnow().date()
    baseline, recent = _split_windows(entries, reference, baseline_window_days, recent_window_days)

    mood = _evaluate_mood(baseline, recent, min_baseline_points, cusum_threshold)
    completion = _evaluate_completion(baseline, recent, min_baseline_points, completion_drop_threshold)
    journal = _evaluate_journal(baseline, recent, min_baseline_points, journal_drop_threshold)

    available = [s for s in (mood, completion, journal) if s.available]

    if not available or len(baseline) < min_baseline_points:
        return DriftResult(status="insufficient-data", mood=mood, completion=completion, journal=journal)

    dipping_count = sum(1 for s in available if s.dipping)

    if dipping_count >= signals_required:
        status = "check-in"
    elif dipping_count == 1:
        status = "gentle-dip"
    else:
        status = "steady"

    return DriftResult(
        status=status,
        mood=mood,
        completion=completion,
        journal=journal,
        dipping_count=dipping_count,
    )
