# backend/app/models/debate.py
"""Bull and Bear case models for AI Debate Mode."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BullCase(BaseModel):
    """Structured bullish investment case from the Bull Agent."""

    ticker: str
    thesis: str = Field(
        description=(
            "A cohesive FUTURE-FACING narrative paragraph of 3-4 sentences making the bullish case "
            "for the NEXT 12-24 MONTHS. Focus on strategic positioning, upcoming catalysts, and market "
            "psychology. Use forward-looking language: 'expected to capitalize on', 'positioned to benefit from'. "
            "CRITICAL: No bullet points, no numbered lists, no mathematical breakdowns. Flowing prose only. "
            "Do NOT repeat data points already in key_strengths — analyze what they imply for the future."
        )
    )


class BearCase(BaseModel):
    """Structured bearish investment case from the Bear Agent."""

    ticker: str
    thesis: str = Field(
        description=(
            "A cohesive FUTURE-FACING narrative paragraph of 3-4 sentences making the bearish case "
            "for the NEXT 12-24 MONTHS. Focus on structural vulnerabilities, upcoming risk catalysts, and "
            "market psychology. Use forward-looking language: 'vulnerable to future shifts in', "
            "'at risk of deteriorating', 'faces increasing pressure from'. "
            "CRITICAL: No bullet points, no numbered lists, no mathematical breakdowns. Flowing prose only. "
            "Do NOT repeat data points already in key_risks — analyze what they imply for the future."
        )
    )
