"""LangGraph-based agents.

Each agent is exposed as both a compiled LangGraph (for orchestration
inside a larger graph) and a thin `run_*` helper (for standalone use,
testing, or one-off invocation from a FastAPI endpoint).
"""
