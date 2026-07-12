from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Mood = Literal["Thriving", "Grounded", "Low", "Blocked"]


class DailyEntry(BaseModel):
    """One day of a user's logged activity. Missing days are fine — just
    omit them from the list; they're treated as gaps, not zeros."""

    date: date
    mood: Mood | None = None
    tasks_completed: int = Field(default=0, ge=0)
    tasks_total: int = Field(default=0, ge=0)
    journal_length: int = Field(default=0, ge=0)


class DriftRequest(BaseModel):
    entries: list[DailyEntry]
    reference_date: date | None = None


class SignalResult(BaseModel):
    available: bool
    baseline_avg: float | None = None
    recent_avg: float | None = None
    statistic: float | None = None  # CUSUM value for mood, drop for completion/journal
    dipping: bool = False


class DriftResult(BaseModel):
    status: Literal["insufficient-data", "steady", "gentle-dip", "check-in"]
    mood: SignalResult
    completion: SignalResult
    journal: SignalResult
    dipping_count: int = 0
