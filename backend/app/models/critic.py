"""Critic Agent output models.

`CritiqueResult` is the LLM-facing structured-output schema.
`CritiqueReport` is the full output returned to callers and, in Task 2,
fed back into the pipeline as context for the Manager's revision.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CritiqueVerdict(str, Enum):
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"


class IssueSeverity(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    FATAL = "fatal"


class CritiqueIssue(BaseModel):
    """One specific flaw identified in the Manager's synthesis."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(
        description="Which part of the report is flawed, e.g. 'key_strengths[1]', 'overall_view'."
    )
    issue: str = Field(description="What is wrong — one sentence.")
    severity: IssueSeverity


class CritiqueResult(BaseModel):
    """LLM-returned critique (structured output schema)."""

    verdict: CritiqueVerdict
    synthesis_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Critic's assessment of how well the synthesis is grounded in the "
            "supplied data and sentiment (0 = unreliable, 1 = fully grounded)."
        ),
    )
    issues: list[CritiqueIssue] = Field(
        default_factory=list,
        description="Specific flaws found. Empty list when verdict is 'approved'.",
    )
    revision_instruction: str | None = Field(
        default=None,
        description=(
            "A single, specific directive the Manager must act on. "
            "Required when verdict is 'needs_revision'; null otherwise."
        ),
    )


class CritiqueReport(BaseModel):
    """Full Critic Agent output returned to callers."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    critique_result: CritiqueResult
    revision_round: int = Field(ge=1, description="Which revision cycle produced this critique.")
    critiqued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
