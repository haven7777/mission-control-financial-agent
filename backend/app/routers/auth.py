"""GET /api/auth/ping — validates a Master Code without running the pipeline.

Used by the frontend to verify a code before storing it in localStorage.
Returns 200 OK on success; 401/403 from the require_master_code dependency.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.services.limiter import limiter
from app.services.master_code_auth import require_master_code

router = APIRouter(prefix="/api", tags=["auth"])


@router.get(
    "/auth/ping",
    summary="Validate a Master Code (returns 200 if valid, 401/403 otherwise)",
    dependencies=[Depends(require_master_code)],
)
@limiter.limit("10/minute")
def auth_ping(request: Request) -> dict[str, str]:
    return {"status": "ok"}
