"""HTML and PDF rendering for FinalReport using Jinja2 + WeasyPrint."""
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
    from weasyprint import HTML  # lazy: system libs only needed at render time
    html_str = render_report_html(report, rtl=rtl)
    return HTML(string=html_str).write_pdf()
