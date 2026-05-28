"""POST /api/export/pdf — converts a FinalReport JSON body to a downloadable PDF."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.models.manager import FinalReport
from app.services.master_code_auth import require_master_code
from app.services.pdf_renderer import render_report_pdf
from app.services.limiter import limiter

router = APIRouter(prefix="/api", tags=["export"])
log = logging.getLogger(__name__)


@router.post(
    "/export/pdf",
    response_class=StreamingResponse,
    summary="Export a FinalReport as a downloadable A4 PDF",
    dependencies=[Depends(require_master_code)],
)
@limiter.limit("3/minute")
def export_pdf(
    request: Request,
    report: FinalReport,
    rtl: bool = Query(default=False, description="Set true to enable RTL layout (Hebrew)"),
) -> StreamingResponse:
    pdf_bytes = render_report_pdf(report, rtl=rtl)
    filename = f"{report.ticker.upper()}_deep_research.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
