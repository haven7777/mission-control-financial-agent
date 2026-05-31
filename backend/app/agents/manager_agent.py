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
from app.utils.llm_retry import llm_retry
from app.utils.sanitize import sanitize_bull_thesis, sanitize_bear_thesis

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
    '   "deep_narrative": "<paragraphs or null>",\n'
    '   "executive_summary": "<3-4 sentence paragraph or null>"}  // executive_summary null in FAST mode\n\n'
    "Be balanced. Acknowledge uncertainty. If fundamentals and sentiment "
    "disagree, call that out explicitly. When a bull/bear debate is provided, "
    "use it to calibrate your overall_view and one_line_summary — do NOT copy "
    "bull/bear arguments into key_strengths or key_risks. Each field has a "
    "distinct structural role (see Section Separation Rules below). "
    "Do not invent facts.\n\n"
    "## Section Separation Rules\n\n"
    "The report has four structurally distinct sections. Writing the same content in two sections "
    "is a critical failure. Each section has one job:\n\n"
    "  key_strengths / key_risks — CURRENT FACTS ONLY\n"
    "    Terse, present-tense data snapshots: specific percentages, named ratios, product lines, "
    "SEC section headings, balance sheet figures. One fact per bullet. "
    "NEVER use forward-looking language ('could', 'may', 'if', 'expected'). "
    "NEVER restate or paraphrase content from bull_case or bear_case. "
    "Example of correct: 'Revenue growth YoY: 23.6%' or 'Debt/equity: 0.42'. "
    "Example of wrong: 'Strong revenue growth positions the company to capitalize on demand' "
    "(that belongs in the bull thesis, not here).\n\n"
    "  bull_case.thesis / bear_case.thesis — FUTURE-FACING NARRATIVE ONLY\n"
    "    Strategic investment story focused on the NEXT 12-24 MONTHS. Flowing prose only — "
    "no bullet points, dashes, numbered lists, or mathematical breakdowns anywhere in the text. "
    "Use forward-looking language: 'expected to capitalize on', 'positioned to benefit from', "
    "'vulnerable to future shifts in', 'strategic momentum toward', 'over the next 12 months'. "
    "CRITICAL: Do NOT repeat exact data points already listed in key_strengths or key_risks. "
    "Instead, ANALYZE what those data points mean for the future. "
    "Do NOT describe the 52-week price range or recent price history — the user sees that in the data panel. "
    "A reader should finish the thesis understanding the FUTURE investment story, not the current data.\n\n"
    "  ENFORCEMENT: Before finalising, scan your output. If any sentence or data point appears "
    "in both the bullet sections and the narrative sections, delete it from the narrative and "
    "replace it with forward-looking analysis of what that fact implies.\n\n"
    "## Anti-Contradiction Guardrail\n\n"
    "Each specific financial metric belongs to either the bull OR the bear case — not both — "
    "unless you supply explicit qualifying context for the duality.\n\n"
    "  Rule: If you cite a metric (P/E, Debt/Equity, operating margin, free cash flow, revenue growth, "
    "gross margin) in key_risks or the bear_case, you CANNOT also cite it in key_strengths or the "
    "bull_case without a specific qualifying phrase — for example: 'P/E is elevated at 35x but "
    "compressing toward sector median as earnings accelerate' is legitimate dual-use. Simply citing "
    "the same P/E as both a risk AND a strength with no qualification is a logical contradiction "
    "and a report failure.\n\n"
    "  Rule: Pick a side for each metric based on industry averages and the supplied context. "
    "If a metric is genuinely ambiguous, acknowledge the ambiguity in ONE section only, then move on.\n\n"
    "## overall_view Selection Rules\n\n"
    "Do NOT default to 'mixed' out of laziness simply because a stock has standard "
    "pros and cons — every stock does. Weigh the evidence and take a definitive stance "
    "('positive' or 'negative'), or qualify it within your one_line_summary "
    "(e.g., 'cautiously bullish' or 'cautiously bearish'). "
    "Reserve 'mixed' strictly for one of these three scenarios:\n"
    "  1. The opposing catalysts are genuinely balanced — roughly a 45/55 split in "
    "evidence weight where neither side clearly dominates.\n"
    "  2. The stock is trading completely sideways with no clear future catalysts in "
    "either direction.\n"
    "  3. A massive binary uncertainty exists (e.g., pending major litigation outcome, "
    "regulatory approval decision, or sudden CEO departure) that makes leaning either "
    "way irresponsible without resolution of that event.\n"
    "Use 'neutral' when the data is thin, the company is in a stable low-volatility "
    "holding pattern, or news coverage is purely informational with no directional signal.\n\n"
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
    "Generate deep_narrative when RESEARCH_MODE is DEEP, OR when filings_context is non-empty. "
    "In FAST mode without filings, set deep_narrative to null.\n\n"
    "Content rules based on available context:\n"
    "  - filings AND transcript present: write 3 paragraphs (SEC Analysis, Exec Subtext, Verdict)\n"
    "  - filings only (no transcript): write 2 paragraphs (SEC Analysis + Verdict). "
    "Begin Verdict: 'Note: No earnings call transcript was available for this analysis.'\n"
    "  - neither filings nor transcript (DEEP mode only): write 1 paragraph. Cite key quantitative "
    "metrics from the data. Name one forward indicator to monitor. Begin: 'Deep Research Note: "
    "SEC filing and transcript data were unavailable for this analysis.'\n\n"
    "Paragraph definitions:\n"
    "  SEC Analysis: Quote exact names of 2-3 risk factor section headings from filings_context. "
    "Include specific financial metrics (revenue, margins, debt ratios). Explain materiality.\n"
    "  Exec Subtext: Quote at least one specific executive statement verbatim from transcript_context. "
    "Analyse evasion signals, hedging language, or omissions. Name dodged questions.\n"
    "  Verdict: State bull-vs-bear conviction level. Name one forward indicator. 3-4 sentences.\n\n"
    "Do not add headers inside deep_narrative. Prose only.\n\n"
    "## Executive Summary (executive_summary field)\n\n"
    "Generate executive_summary ONLY when RESEARCH_MODE is DEEP. In FAST mode, set to null.\n\n"
    "Write a SINGLE dense paragraph of 3-4 sentences (60-90 words). "
    "Sentence 1: Core investment thesis with conviction level. "
    "Sentence 2: Valuation context (P/E vs. sector norms, growth vs. price, margin trajectory). "
    "Sentence 3: Primary risk and its materiality to the thesis. "
    "Sentence 4: Forward catalyst or monitoring signal that would change the verdict. "
    "Ground every sentence in the specific data supplied. NEVER return a single sentence. "
    "NEVER use generic language — cite specific numbers and company details.\n\n"
    "CRITICAL PENALTY: Your executive_summary MUST be a thick, multi-sentence paragraph "
    "synthesizing the valuation, SEC risk, and overall thesis. If it is a single sentence, "
    "the output is considered a failure.\n\n"
    "## Analytical Guardrails\n\n"
    "Consistency: The bull_case and bear_case must not contradict the same factual claim. "
    "If the bull case cites strong revenue growth, the bear case must not deny it — it should "
    "argue that growth is priced in, decelerating, or offset by another risk. Facts are shared; "
    "interpretations diverge.\n\n"
    "Proportionality: Match language intensity to magnitude. A daily price move of less than 2% "
    "must not be described as a 'massive sell-off,' 'crash,' or 'collapse.' A weekly move under "
    "10% must not be called 'dramatic' or 'unprecedented.' Use precise language: '0.4% decline,' "
    "'modest pullback,' 'slight underperformance.' Reserve strong language (surge, plunge, "
    "rout, rally) for moves that actually warrant it (>5% daily, >15% weekly, or multi-sigma events).\n\n"
    "## Transcript Guardrail\n\n"
    "CRITICAL: If transcript_context is absent or empty, you MUST NOT invent, fabricate, "
    "or paraphrase executive statements, earnings call quotes, management commentary, or "
    "conference call remarks in ANY section of your output (key_strengths, key_risks, "
    "deep_narrative, or executive_summary). Do not write phrases like 'management noted,' "
    "'the CEO stated,' or 'in the earnings call' unless transcript_context explicitly "
    "contains that information. Any reference to executive tone or forward guidance must "
    "cite transcript_context verbatim or not appear at all."
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
    is_deep_mode: bool = False


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

    fm = data.financial_metrics
    if fm:
        def _pct(v: object) -> str:
            return f"{float(v)*100:.1f}%" if v is not None else "N/A"
        def _fmt(v: object, fmt: str = ".2f") -> str:
            return format(float(v), fmt) if v is not None else "N/A"
        if fm.get("revenue_ttm") is not None:
            lines.append(f"Revenue TTM: ${fm['revenue_ttm']:,}")
        lines.append(
            f"Margins — Gross: {_pct(fm.get('gross_margin'))}, "
            f"Operating: {_pct(fm.get('operating_margin'))}, "
            f"Net: {_pct(fm.get('net_margin'))}"
        )
        lines.append(
            f"Debt/Equity: {_fmt(fm.get('debt_to_equity'))}, "
            f"ROE: {_pct(fm.get('roe'))}, "
            f"Revenue growth YoY: {_pct(fm.get('revenue_growth_yoy'))}"
        )

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
        
        content_text = (ca.article.content or "").strip()[:1000]
        if content_text:
            lines.append(f"      content: {content_text}...")
            
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

    model_name = settings.openai_deep_model if state.is_deep_mode else settings.openai_model
    llm = ChatOpenAI(
        model=model_name,
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
        user_payload += (
            f"\n\nBULL CASE:\n{state.bull_case.thesis}"
            f"\n\nBEAR CASE:\n{state.bear_case.thesis}"
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

    user_payload += f"\n\nRESEARCH_MODE: {'DEEP' if state.is_deep_mode else 'FAST'}"

    if state.revision_instruction:
        user_payload = (
            f"REVISION REQUIRED — your previous synthesis was rejected by the auditor.\n"
            f"You MUST address this specific issue before re-synthesizing:\n"
            f"  {state.revision_instruction}\n\n"
        ) + user_payload

    log.info("manager_agent: synthesizing for %s via OpenAI (%s)%s",
             state.data.ticker, model_name,
             " [REVISION]" if state.revision_instruction else "")

    @llm_retry
    def _invoke() -> ManagerSynthesis:
        return structured.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_payload),
        ])

    synthesis: ManagerSynthesis = _invoke()
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
    is_deep_mode: bool = False,
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
        "is_deep_mode": is_deep_mode,
    })
    synthesis: ManagerSynthesis = (
        result["synthesis"] if isinstance(result, dict) else result.synthesis
    )
    if synthesis is None:
        raise RuntimeError("Manager graph finished with no synthesis in state")

    settings = get_settings()
    model_used = settings.openai_deep_model if is_deep_mode else settings.openai_model

    # Strip any bullet lists the LLM appended to prose-only narrative fields.
    # This is a hard architectural guarantee — prompts alone cannot be trusted.
    clean_bull = (
        bull_case.model_copy(update={"thesis": sanitize_bull_thesis(bull_case.thesis)})
        if bull_case else None
    )
    clean_bear = (
        bear_case.model_copy(update={"thesis": sanitize_bear_thesis(bear_case.thesis)})
        if bear_case else None
    )

    return FinalReport(
        ticker=data.ticker,
        company_name=data.overview.name,
        overall_view=synthesis.overall_view,
        one_line_summary=synthesis.one_line_summary,
        key_strengths=synthesis.key_strengths,
        key_risks=synthesis.key_risks,
        data_snapshot=data,
        sentiment_snapshot=sentiment,
        model_used=model_used,
        bull_case=clean_bull,
        bear_case=clean_bear,
        filings_context=filings_context,
        transcript_context=transcript_context,
        deep_narrative=synthesis.deep_narrative,
        executive_summary=synthesis.executive_summary,
    )


__all__ = [
    "run_manager_agent",
    "ManagerAgentError",
    "MissingLLMKey",
]
