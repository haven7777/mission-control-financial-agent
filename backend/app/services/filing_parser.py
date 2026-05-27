"""SEC filing HTML parser.

Extracts the Risk Factors (Item 1A) and MD&A (Item 7) sections from a
10-K/10-Q HTML document and splits them into overlapping text chunks
suitable for embedding.

Strategy:
  1. Strip HTML tags with BeautifulSoup to get clean plain text.
  2. Use regex to locate section boundaries in the plain text. We take
     the *last* occurrence of an item header because the table of
     contents also contains the same header text — the actual section
     comes after the TOC.
  3. Cap each section at 15 000 chars before chunking to keep embedding
     cost predictable.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

_MAX_SECTION_CHARS = 15_000
_CHUNK_SIZE = 1_500
_CHUNK_OVERLAP = 150

_SECTION_STARTS: dict[str, list[str]] = {
    "risk_factors": [
        r"item\s+1a[\.\s ]",
        r"risk\s+factors",
    ],
    "mda": [
        r"item\s+7[\.\s ](?!a)",   # Item 7 but not 7A
        r"item\s+2[\.\s ](?!a)",   # 10-Q uses Item 2 for MD&A
        r"management[\s'']+s\s+discussion",
    ],
}

_SECTION_ENDS: dict[str, list[str]] = {
    "risk_factors": [r"item\s+1b[\.\s ]", r"item\s+2[\.\s ]"],
    "mda": [r"item\s+7a[\.\s ]", r"item\s+3[\.\s ]", r"item\s+8[\.\s ]"],
}


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n", strip=True)


def _find_section(text: str, section: str) -> str:
    text_lower = text.lower()
    start_pos = -1

    for pattern in _SECTION_STARTS[section]:
        matches = list(re.finditer(pattern, text_lower))
        if matches:
            # Last match skips the table-of-contents occurrence
            start_pos = matches[-1].start()
            break

    if start_pos == -1:
        return ""

    end_pos = len(text)
    search_region = text_lower[start_pos + 200:]  # skip the header itself
    for pattern in _SECTION_ENDS[section]:
        m = re.search(pattern, search_region)
        if m:
            end_pos = min(end_pos, start_pos + 200 + m.start())
            break

    raw = text[start_pos:end_pos].strip()
    return raw[:_MAX_SECTION_CHARS]


def extract_sections(html: str) -> dict[str, str]:
    """Return {'risk_factors': '...', 'mda': '...'} from a 10-K HTML document.

    Values are plain text, capped at 15 000 chars each. An empty string
    means the section was not found.
    """
    text = _html_to_text(html)
    return {
        "risk_factors": _find_section(text, "risk_factors"),
        "mda": _find_section(text, "mda"),
    }


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split *text* into overlapping chunks of at most *chunk_size* characters.

    Tries to break at a sentence boundary ('. ') near the chunk end to
    avoid splitting mid-sentence. Returns only chunks with >= 100 chars.
    """
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(". ", start + chunk_size - overlap, end)
            if boundary != -1:
                end = boundary + 1  # include the period
        chunk = text[start:end].strip()
        if len(chunk) >= 100:
            chunks.append(chunk)
        next_start = end - overlap
        if next_start <= start:
            break
        start = next_start
    return chunks
