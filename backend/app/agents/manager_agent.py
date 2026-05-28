"""Manager Agent — synthesizes Data + Sentiment into a FinalReport.

Single-node LangGraph; the synthesis itself is a structured-output LLM
call bound to `ManagerSynthesis`, so any drift surfaces as a typed
ValidationError. Inputs are taken as already-built typed reports from
the Data and Sentiment agents — orchestrating *who runs first* is a
separate concern (see the planned pipeline graph + FastAPI endpoint).

Public entry point: `run_manager_agent(data_report, sentiment_report)
-> FinalReport`.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.models.agents import DataAgentReport
from app.models.debate import BullCase, BearCase
from app.models.filings import FilingsContext
from app.models.transcript import TranscriptContext
from app.models.manager import FinalReport, ManagerSynthesis
from app.models.sentiment import SentimentAgentReport

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior investment analyst. You will receive:\n"
    "  (1) Financial / fundamental data for a publicly-traded stock.\n"
    "  (2) Sentiment from recent news coverage.\n"
    "  (3) Optionally: a structured bull/bear debate from specialist analysts.\n"
    "  (4) Optionally: verbatim excerpts from the company's latest SEC 10-K filing "
    "(Risk Factors and MD&A). When present, treat these as primary sources — "
    "quote or paraphrase them directly in your strengths and risks.\n"
    "  (5) Optionally: earnings call transcript analysis including executive tone, "
    "forward-looking statements, and analyst questions management appeared to dodge. "
    "When present, factor the tone and any evasive responses into your risk assessment.\n\n"
    "Synthesize everything into a balanced, investor-facing brief. Respond as "
    "a JSON object matching this schema:\n"
    '  {"overall_view": "positive"|"negative"|"mixed"|"neutral",\n'
    '   "one_line_summary": "<one sentence>",\n'
    '   "key_strengths": ["<sentence>", ...],   // 2-6 items\n'
    '   "key_risks":     ["<sentence>", ...],   // 2-6 items\n'
    '   "deep_narrative": "<three paragraphs or null>"}  // null when filings or transcript absent\n\n'
    "Be balanced. Acknowledge uncertainty. If fundamentals and sentiment "
    "disagree, call that out explicitly. When a bull/bear debate is provided, "
    "engage with the strongest arguments from both sides in your strengths and "
    "risks. Each bullet must be grounded in the supplied data. Do not invent facts.\n\n"
    "Where the supplied data suggests Israeli market relevance — such as a TASE or "
    "dual-listed company, NIS-denominated revenues, or Israeli headquarters — consider "
    "these contextual factors where material: "
    "(1) NIS/USD currency exposure affects USD-denominated returns for foreign investors "
    "and introduces FX risk that should be noted in the risk section; "
    "(2) Israeli individual investors pay 25% capital gains tax (vs. varied US rates), "
    "which can affect the investment case for the local retail segment; "
    "(3) dual-listed companies may trade at a premium or discount on TASE vs. NASDAQ "
    "due to differing liquidity and investor composition — call this out if significant; "
    "(4) Israeli tech-sector strengths (cybersecurity, semiconductor IP, enterprise SaaS, "
    "defense tech) can justify premium valuations — flag when applicable; "
    "(5) geopolitical or IDF reserve-duty events can cause temporary operational "
    "disruption or sentiment shocks for Israeli-headquartered firms — mention as a risk "
    "factor when the company is Israeli-domiciled. "
    "Apply these factors only when they are material and grounded in the supplied data."
    "\n\n## Deep Narrative (deep_narrative field)\n\n"
    "Generate deep_narrative ONLY when BOTH filings_context AND transcript_context are "
    "non-empty in the inputs. If either is absent, set deep_narrative to null.\n\n"
    "When generating deep_narrative, write EXACTLY three paragraphs separated by blank lines:\n\n"
    "Paragraph 1 — SEC Filing Analysis: Quote the exact names of 2-3 risk factor section "
    "headings from filings_context. Include specific financial metrics (revenue, margins, "
    "debt ratios) drawn from the data. Explain why each risk is material to the investment thesis.\n\n"
    "Paragraph 2 — Earnings Call Subtext: Quote at least one specific executive statement "
    "verbatim from transcript_context. Analyse what each quote reveals through evasion signals, "
    "hedging language, or conspicuous omissions. Be specific — name the question that was "
    "dodged, if applicable.\n\n"
    "Paragraph 3 — Verdict: State a clear bull-vs-bear conviction level (e.g., 'Cautiously "
    "bullish'). Name the single most important forward indicator an investor should monitor. "
    "Keep to 3-4 sentences.\n\n"
    "Do not add headers inside deep_narrative. Prose only."
)


# --- Exceptions --------------------------------------------------------------

class ManagerAgentError(Exception):
    """Base class for Manager Agent failures."""


class MissingLLMKey(ManagerAgentError):
    """No Groq key configured."""


# --- Graph state -------------------------------------------------------------

class _ManagerAgentState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: DataAgentReport
    sentiment: SentimentAgentReport
    synthesis: ManagerSynthesis | None = None
    revision_instruction: str | None = None
    bull_case: BullCase | None = None
    bear_case: BearCase | None = None
    filings_context: FilingsContext | None = None
    transcript_context: TranscriptContext | None = None


# --- Prompt formatting -------------------------------------------------------

def _format_data(data: DataAgentReport) -> str:
    o = data.overview
    q = data.quote
    lines = [
        f"Company: {o.name} ({o.symbol}) — sector {o.sector} / industry {o.industry}",
        f"Listing: {o.exchange}, currency {o.currency}, country {o.country}",
        f"Recent price: {q.price} on {q.latest_trading_day} "
        f"(change {q.change} = {q.change_percent}%)",
        f"Day range: {q.low} – {q.high}; previous close {q.previous_close}; volume {q.volume:,}",
    ]
    if o.market_capitalization is not None:
        lines.append(f"Market cap: {o.market_capitalization:,}")
    if o.pe_ratio is not None:
        lines.append(f"P/E ratio: {o.pe_ratio}")
    if o.eps is not None:
        lines.append(f"EPS: {o.eps}")
    if o.dividend_yield is not None:
        lines.append(f"Dividend yield: {o.dividend_yield}")
    if o.beta is not None:
        lines.append(f"Beta: {o.beta}")
    if o.week_52_high is not None and o.week_52_low is not None:
        in_band = data.is_within_52_week_band
        lines.append(
            f"52-week range: {o.week_52_low} – {o.week_52_high} "
            f"(current price inside band: {in_band})"
        )
    if o.analyst_target_price is not None:
        lines.append(f"Analyst target price: {o.analyst_target_price}")
    desc = (o.description or "").strip()
    if desc:
        lines.append(f"Description: {desc[:600]}{'...' if len(desc) > 600 else ''}")
    return "\n".join(lines)


def _format_sentiment(sent: SentimentAgentReport) -> str:
    if sent.is_zero_news:
        return (
            "NEWS SENTIMENT: No market news articles were found for this ticker. "
            "Sentiment analysis is unavailable. Base your synthesis on the "
            "quantitative fundamentals only and note the absence of news coverage."
        )
    lines = [
        f"Overall news sentiment: {sent.overall_sentiment.value} "
        f"(confidence {sent.overall_confidence:.2f})",
        f"Articles analyzed: {sent.articles_analyzed}",
        "Per-article breakdown:",
    ]
    for i, ca in enumerate(sent.classified, start=1):
        lines.append(
            f"  [{i}] {ca.sentiment.value} ({ca.confidence:.2f}) — {ca.article.title}"
        )
        lines.append(f"      reason: {ca.reason}")
    return "\n".join(lines)


def _format_filings(ctx: FilingsContext) -> str:
    if ctx.is_empty or not ctx.chunks:
        return ""
    lines = [f"SEC FILING CONTEXT ({ctx.form_type} — sourced from EDGAR):"]
    for chunk in ctx.chunks:
        label = "Risk Factors" if chunk.section == "risk_factors" else "MD&A"
        lines.append(f"\n[{label}]\n{chunk.content}")
    return "\n".join(lines)


def _format_transcript(ctx: TranscriptContext) -> str:
    if ctx.is_empty:
        return ""
    lines = [
        f"EARNINGS CALL TRANSCRIPT (Q{ctx.quarter} {ctx.year}"
        + (f" — {ctx.date[:10]}" if ctx.date else "")
        + "):",
        f"Executive Tone: {ctx.executive_tone.title()}",
        f"Management Sentiment: {ctx.management_sentiment.title()}",
    ]
    if ctx.key_forward_statements:
        lines.append("\nKey Forward-Looking Statements:")
        for stmt in ctx.key_forward_statements:
            lines.append(f"  • {stmt}")
    if ctx.dodged_questions:
        lines.append(
            f"\nAnalyst Questions With Potentially Evasive Responses ({len(ctx.dodged_questions)}):"
        )
        for i, dq in enumerate(ctx.dodged_questions, 1):
            lines.append(f"  {i}. Q: {dq.analyst_question}")
            lines.append(f'     A: "{dq.management_response}"')
            lines.append(f"     Why evasive: {dq.evasion_signal}")
    return "\n".join(lines)


# --- Nodes -------------------------------------------------------------------

def _synthesize_node(state: _ManagerAgentState) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise MissingLLMKey("OPENAI_API_KEY is not set in backend/.env")

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.0,
    )
    # `method="json_mode"` makes Groq emit raw JSON (no `<function=...>{...}`
    # tool wrapper) and Pydantic validates client-side. Avoids the
    # malformed-tool-envelope failure we hit on `llama-3.3-70b-versatile`
    # under the default `function_calling` method, while staying compatible
    # with models that don't support `json_schema` strict mode.
    structured = llm.with_structured_output(ManagerSynthesis, method="json_mode")

    data_block = _format_data(state.data)
    sentiment_block = _format_sentiment(state.sentiment)
    user_payload = (
        f"TICKER: {state.data.ticker}\n\n"
        f"FUNDAMENTALS & PRICE:\n{data_block}\n\n"
        f"NEWS SENTIMENT:\n{sentiment_block}"
    )

    if state.bull_case and state.bear_case:
        bull_args = "\n".join(f"  • {a}" for a in state.bull_case.key_arguments)
        bear_args = "\n".join(f"  • {a}" for a in state.bear_case.key_arguments)
        user_payload += (
            f"\n\nBULL CASE (strongest upside arguments):\n"
            f"Thesis: {state.bull_case.thesis}\n{bull_args}"
            f"\n\nBEAR CASE (strongest downside arguments):\n"
            f"Thesis: {state.bear_case.thesis}\n{bear_args}"
            f"\n\nWeigh the bull and bear cases above when forming your final view."
        )

    if state.filings_context and not state.filings_context.is_empty:
        filings_block = _format_filings(state.filings_context)
        if filings_block:
            user_payload += f"\n\n{filings_block}"

    if state.transcript_context and not state.transcript_context.is_empty:
        transcript_block = _format_transcript(state.transcript_context)
        if transcript_block:
            user_payload += f"\n\n{transcript_block}"

    if state.revision_instruction:
        user_payload = (
            f"REVISION REQUIRED — your previous synthesis was rejected by the auditor.\n"
            f"You MUST address this specific issue before re-synthesizing:\n"
            f"  {state.revision_instruction}\n\n"
        ) + user_payload

    log.info("manager_agent: synthesizing for %s via OpenAI (%s)%s",
             state.data.ticker, settings.openai_model,
             " [REVISION]" if state.revision_instruction else "")
    synthesis: ManagerSynthesis = structured.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_payload),
    ])
    return {"synthesis": synthesis}


def _build_graph():
    graph: StateGraph = StateGraph(_ManagerAgentState)
    graph.add_node("synthesize", _synthesize_node)
    graph.add_edge(START, "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


_compiled_graph = _build_graph()


# --- Public API --------------------------------------------------------------

def run_manager_agent(
    data: DataAgentReport,
    sentiment: SentimentAgentReport,
    revision_instruction: str | None = None,
    bull_case: BullCase | None = None,
    bear_case: BearCase | None = None,
    filings_context: FilingsContext | None = None,
    transcript_context: TranscriptContext | None = None,
) -> FinalReport:
    """Run the synthesis graph and return a `FinalReport`.

    Pass *revision_instruction* on subsequent calls to include the Critic's
    specific directive in the prompt, forcing the Manager to address the flaw.
    Pass *bull_case* and *bear_case* to enable debate-mode synthesis, where
    the Manager weighs the structured bull/bear arguments in its final view.
    """
    if data.ticker != sentiment.ticker:
        raise ValueError(
            f"data/sentiment ticker mismatch: {data.ticker!r} vs {sentiment.ticker!r}"
        )

    result = _compiled_graph.invoke({
        "data": data,
        "sentiment": sentiment,
        "revision_instruction": revision_instruction,
        "bull_case": bull_case,
        "bear_case": bear_case,
        "filings_context": filings_context,
        "transcript_context": transcript_context,
    })
    synthesis: ManagerSynthesis = (
        result["synthesis"] if isinstance(result, dict) else result.synthesis
    )
    if synthesis is None:
        raise RuntimeError("Manager graph finished with no synthesis in state")

    return FinalReport(
        ticker=data.ticker,
        company_name=data.overview.name,
        overall_view=synthesis.overall_view,
        one_line_summary=synthesis.one_line_summary,
        key_strengths=synthesis.key_strengths,
        key_risks=synthesis.key_risks,
        data_snapshot=data,
        sentiment_snapshot=sentiment,
        model_used=get_settings().openai_model,
        bull_case=bull_case,
        bear_case=bear_case,
        filings_context=filings_context,
        transcript_context=transcript_context,
        deep_narrative=synthesis.deep_narrative,
    )


__all__ = [
    "run_manager_agent",
    "ManagerAgentError",
    "MissingLLMKey",
]
