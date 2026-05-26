"""Smoke test: verify LangSmith tracing wiring.

Tests the configure_langsmith_tracing() function directly:
  - with a real key + tracing=true  → env vars are set in os.environ
  - with no key                     → env vars are NOT set, function returns False
  - idempotency                     → calling twice is harmless

Also verifies the /health endpoint exposes langsmith_tracing.
Does NOT make a live LangSmith API call (no network required).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch, MagicMock

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
errors = 0


def check(label: str, condition: bool) -> None:
    global errors
    print(f"  [{ PASS if condition else FAIL}] {label}")
    if not condition:
        errors += 1


# ── configure_langsmith_tracing() with tracing enabled ───────────────────────
print("\n── tracing enabled (key + flag set) ──")

FAKE_KEY = "ls__test_key_abc123"
FAKE_PROJECT = "test-project"
FAKE_ENDPOINT = "https://api.smith.langchain.com"

fake_settings = MagicMock()
fake_settings.langsmith_configured = True
fake_settings.langsmith_api_key = FAKE_KEY
fake_settings.langsmith_project = FAKE_PROJECT
fake_settings.langsmith_endpoint = FAKE_ENDPOINT

# Clean up any leftover env vars from previous runs
for k in ["LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGSMITH_PROJECT",
          "LANGSMITH_ENDPOINT", "LANGCHAIN_TRACING_V2",
          "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT"]:
    os.environ.pop(k, None)

with patch("app.config.get_settings", return_value=fake_settings):
    from app.services.tracing import configure_langsmith_tracing
    result = configure_langsmith_tracing()

check("returns True when configured", result is True)
check("LANGSMITH_API_KEY set in os.environ", os.environ.get("LANGSMITH_API_KEY") == FAKE_KEY)
check("LANGSMITH_TRACING=true in os.environ", os.environ.get("LANGSMITH_TRACING") == "true")
check("LANGSMITH_PROJECT set", os.environ.get("LANGSMITH_PROJECT") == FAKE_PROJECT)
check("LANGSMITH_ENDPOINT set", os.environ.get("LANGSMITH_ENDPOINT") == FAKE_ENDPOINT)
check("LANGCHAIN_TRACING_V2=true set (compat)", os.environ.get("LANGCHAIN_TRACING_V2") == "true")
check("LANGCHAIN_API_KEY set (compat)", os.environ.get("LANGCHAIN_API_KEY") == FAKE_KEY)
check("LANGCHAIN_PROJECT set (compat)", os.environ.get("LANGCHAIN_PROJECT") == FAKE_PROJECT)

# ── idempotency ───────────────────────────────────────────────────────────────
print("\n── idempotency ──")
os.environ["LANGSMITH_API_KEY"] = "existing_value"  # pre-set

with patch("app.config.get_settings", return_value=fake_settings):
    configure_langsmith_tracing()

check("setdefault does not overwrite pre-existing value",
      os.environ.get("LANGSMITH_API_KEY") == "existing_value")

os.environ["LANGSMITH_API_KEY"] = FAKE_KEY  # restore

# ── no key → tracing disabled ─────────────────────────────────────────────────
print("\n── tracing disabled (no key) ──")

for k in ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"]:
    os.environ.pop(k, None)

disabled_settings = MagicMock()
disabled_settings.langsmith_configured = False

with patch("app.config.get_settings", return_value=disabled_settings):
    result_off = configure_langsmith_tracing()

check("returns False when not configured", result_off is False)
check("LANGSMITH_API_KEY not set", "LANGSMITH_API_KEY" not in os.environ)

# ── /health exposes langsmith_tracing ────────────────────────────────────────
print("\n── /health endpoint includes langsmith_tracing ──")

# Patch everything that might do real I/O during app import
with (
    patch("app.services.tracing.configure_langsmith_tracing", return_value=True),
    patch("app.services.alpha_vantage.fetch_global_quote", return_value=MagicMock()),
    patch("app.services.alpha_vantage.fetch_company_overview", return_value=MagicMock()),
):
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/health")

check("/health returns 200", resp.status_code == 200)
body = resp.json()
check("langsmith_tracing key present in /health", "langsmith_tracing" in body)
print(f"  /health body: {body}")

# ── summary ───────────────────────────────────────────────────────────────────
print(f"\n{'All checks passed.' if errors == 0 else f'{errors} check(s) failed.'}")
sys.exit(0 if errors == 0 else 1)
