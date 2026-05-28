"""HTML and PDF rendering for FinalReport using Jinja2 + Playwright (Chromium)."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.manager import FinalReport

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
)


def render_report_html(report: FinalReport, *, rtl: bool = False) -> str:
    template = _jinja_env.get_template("report.html.j2")
    return template.render(report=report, rtl=rtl)


def render_report_pdf(report: FinalReport, *, rtl: bool = False) -> bytes:
    from playwright.sync_api import sync_playwright
    html_str = render_report_html(report, rtl=rtl)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_str, wait_until="networkidle")
        pdf = page.pdf(format="A4", print_background=True)
        browser.close()
    return pdf
