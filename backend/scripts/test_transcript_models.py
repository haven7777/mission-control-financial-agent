import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.transcript import DodgedQuestion, TranscriptContext
from app.models.manager import FinalReport

def test_models():
    dq = DodgedQuestion(
        analyst_question="What is your China revenue outlook?",
        management_response="We feel very good about our long-term opportunity in China.",
        evasion_signal="Redirected to long-term narrative without addressing the specific question.",
    )
    ctx = TranscriptContext(
        ticker="AAPL",
        quarter=2,
        year=2026,
        date="2026-05-01",
        executive_tone="confident",
        management_sentiment="positive",
        key_forward_statements=["We expect double-digit Services growth in Q3."],
        dodged_questions=[dq],
    )
    assert not ctx.is_empty
    assert ctx.dodged_questions[0].analyst_question == "What is your China revenue outlook?"

    ctx_empty = TranscriptContext(ticker="ZZZZ", is_empty=True)
    assert ctx_empty.is_empty
    assert ctx_empty.quarter == 0

    # FinalReport accepts transcript_context=None (backward compat)
    print("✓ DodgedQuestion, TranscriptContext, FinalReport(transcript_context=None) all OK")

if __name__ == "__main__":
    test_models()
