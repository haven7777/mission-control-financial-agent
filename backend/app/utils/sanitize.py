"""Post-processing sanitizers for LLM narrative fields.

LLMs frequently emit a good narrative paragraph followed by bullet lists
("formatting bleed"), ignoring explicit prose-only instructions. These
utilities strip the trailing lists so bullet points can never reach the
UI or PDF renderer regardless of what the LLM outputs.
"""

from __future__ import annotations

import re

# Matches any line that opens with a bullet marker or a numbered-list prefix.
# Covers: - * + • · ◦ ▪ ▸ ► ● and "1." "1)" "(1)" "1:" variants.
_BULLET_RE = re.compile(
    r"^(?:"
    r"[\-\+\*•·◦▪▸►●]"          # symbol bullets
    r"|(?:\d+[\.\)\:])"           # "1." / "1)" / "1:"
    r"|(?:\(\d+\))"               # "(1)"
    r")"
)


def sanitize_narrative(text: str) -> str:
    """Return only the first contiguous prose block, discarding trailing bullet lists.

    Strategy:
      1. Split on newlines.
      2. Collect lines until the first bullet/numbered-list line is encountered.
      3. Strip trailing blank lines from the collected block.
      4. Collapse any internal runs of 3+ newlines to a single blank line.

    If nothing survives (edge case: the LLM emitted only bullets), the
    original text is returned unchanged so we never silently drop content.
    """
    if not text or not text.strip():
        return text

    lines = text.strip().splitlines()
    narrative_lines: list[str] = []

    for line in lines:
        if _BULLET_RE.match(line.strip()):
            break
        narrative_lines.append(line)

    result = "\n".join(narrative_lines).strip()

    # Collapse 3+ consecutive blank lines that can sneak in mid-paragraph
    result = re.sub(r"\n{3,}", "\n\n", result)

    # Fall back to original if the sanitizer wiped everything
    return result if result else text


def sanitize_bull_thesis(thesis: str) -> str:
    """Convenience wrapper — same as sanitize_narrative, named for call-site clarity."""
    return sanitize_narrative(thesis)


def sanitize_bear_thesis(thesis: str) -> str:
    """Convenience wrapper — same as sanitize_narrative, named for call-site clarity."""
    return sanitize_narrative(thesis)
