import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.transcript_agent import run_transcript_agent
from app.models.transcript import TranscriptContext

def test_transcript_agent():
    print("Running TranscriptAgent for AAPL (may take 10-20s)...")
    ctx = run_transcript_agent("AAPL")

    assert isinstance(ctx, TranscriptContext)
    print(f"is_empty: {ctx.is_empty}")

    if ctx.is_empty:
        print("⚠ TranscriptAgent returned empty context (FMP or OpenAI not configured)")
        return

    print(f"Q{ctx.quarter} {ctx.year} — {ctx.date}")
    print(f"executive_tone: {ctx.executive_tone}")
    print(f"management_sentiment: {ctx.management_sentiment}")

    print(f"\nForward-looking statements ({len(ctx.key_forward_statements)}):")
    for s in ctx.key_forward_statements:
        print(f"  • {s}")

    print(f"\nDodged questions ({len(ctx.dodged_questions)}):")
    for i, dq in enumerate(ctx.dodged_questions, 1):
        print(f"  {i}. Q: {dq.analyst_question}")
        print(f"     A: {dq.management_response[:100]}...")
        print(f"     Signal: {dq.evasion_signal}")

    assert ctx.executive_tone in ("confident", "cautious", "defensive", "neutral")
    assert ctx.management_sentiment in ("positive", "neutral", "negative")
    assert isinstance(ctx.key_forward_statements, list)
    assert isinstance(ctx.dodged_questions, list)
    print("\n✓ TranscriptAgent OK")

if __name__ == "__main__":
    test_transcript_agent()
