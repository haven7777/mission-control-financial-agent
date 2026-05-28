"""Transcript Agent — analyzes earnings call Q&A for executive tone and evasiveness.

Workflow:
  1. Fetch the most recent earnings call transcript from FMP.
  2. Extract the Q&A section (capped at 12 000 chars).
  3. Run gpt-4o-mini with structured output to detect:
     - Executive tone (confident / cautious / defensive / neutral)
     - Management sentiment (positive / neutral / negative)
     - Key forward-looking statements (2-5 bullets)
     - Dodged analyst questions (0-5 instances with evasion signals)

Returns is_empty=True when:
  - FMP_API_KEY or OPENAI_API_KEY not configured
  - FMP has no transcript for the ticker
  - Any unhandled error (never raises)
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.models.transcript import DodgedQuestion, TranscriptContext
from app.services.transcript_fetcher import (
    TranscriptFetchError,
    TranscriptNotFoundError,
    extract_qa_section,
    get_latest_transcript,
)

log = logging.getLogger(__name__)

_MAX_FORWARD_STATEMENTS = 5
_MAX_DODGED_QUESTIONS = 5

_SYSTEM_PROMPT = (
    "You are an expert earnings call analyst specializing in detecting "
    "management communication patterns — especially evasive responses during analyst Q&A.\n\n"
    "Analyze the provided Q&A section and return a JSON object with these fields:\n\n"
    "1. executive_tone: one of 'confident' (clear direct answers, specific guidance given), "
    "'cautious' (hedged language, many caveats, forward guidance withheld), "
    "'defensive' (deflects criticism, avoids specifics under pressure, "
    "pivots away from negative questions), or 'neutral'.\n\n"
    "2. management_sentiment: one of 'positive' (optimistic language, upbeat guidance), "
    "'negative' (guarded tone, warning-heavy, cautious outlook), or 'neutral'.\n\n"
    "3. key_forward_statements: A list of 2-5 specific forward-looking statements — "
    "actual guidance, quantitative targets, product/market expectations. "
    "Quote or closely paraphrase the actual words used.\n\n"
    "4. dodged_questions: A list of 0-5 analyst questions where management gave an evasive "
    "response. Evasive means: (a) explicit deflection ('we don't provide guidance on that'), "
    "(b) redirect to a different, more favorable topic, "
    "(c) vague non-answer when specifics were clearly sought ('we feel good about our position'), "
    "or (d) excessive caveats that avoid committing to anything. "
    "For each dodged question provide: "
    "analyst_question (brief paraphrase of what was asked), "
    "management_response (key excerpt showing the evasion — max 150 chars), "
    "evasion_signal (one sentence explaining what made it evasive)."
)


class _DodgedQuestionResult(BaseModel):
    analyst_question: str
    management_response: str
    evasion_signal: str


class _ExtractionResult(BaseModel):
    executive_tone: Literal["confident", "cautious", "defensive", "neutral"]
    management_sentiment: Literal["positive", "neutral", "negative"]
    key_forward_statements: list[str]
    dodged_questions: list[_DodgedQuestionResult]


def run_transcript_agent(ticker: str) -> TranscriptContext:
    """Return earnings call transcript analysis for ticker.

    Never raises — returns is_empty=True on any failure.
    """
    normalized = ticker.strip().upper()
    settings = get_settings()

    if not settings.fmp_configured or not settings.openai_api_key:
        log.info(
            "transcript_agent: skipping %s — FMP_API_KEY or OPENAI_API_KEY not configured",
            normalized,
        )
        return TranscriptContext(ticker=normalized, is_empty=True)

    try:
        raw = get_latest_transcript(normalized)
        qa_text = extract_qa_section(raw["content"])

        llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.0,
        )
        chain = llm.with_structured_output(_ExtractionResult, method="json_mode")

        user_prompt = (
            f"EARNINGS CALL Q&A — {normalized} Q{raw['quarter']} {raw['year']}\n\n"
            f"{qa_text}\n\n"
            "Return a JSON object with the fields: executive_tone, management_sentiment, "
            "key_forward_statements (list), dodged_questions (list)."
        )

        result: _ExtractionResult = chain.invoke(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )

        return TranscriptContext(
            ticker=normalized,
            quarter=raw["quarter"],
            year=raw["year"],
            date=raw["date"],
            executive_tone=result.executive_tone,
            management_sentiment=result.management_sentiment,
            key_forward_statements=result.key_forward_statements[:_MAX_FORWARD_STATEMENTS],
            dodged_questions=[
                DodgedQuestion(
                    analyst_question=d.analyst_question,
                    management_response=d.management_response[:200],
                    evasion_signal=d.evasion_signal,
                )
                for d in result.dodged_questions[:_MAX_DODGED_QUESTIONS]
            ],
        )

    except TranscriptNotFoundError as exc:
        log.info("transcript_agent: no transcript for %s: %s", normalized, exc)
        return TranscriptContext(ticker=normalized, is_empty=True)
    except TranscriptFetchError as exc:
        log.warning("transcript_agent: fetch failed for %s: %s", normalized, exc)
        return TranscriptContext(ticker=normalized, is_empty=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("transcript_agent: unexpected error for %s: %s", normalized, exc)
        return TranscriptContext(ticker=normalized, is_empty=True)
