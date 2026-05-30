"""GET /api/auth/ping — validates a Master Code and returns its credit grant.

Returns 200 {"status": "ok", "credits": N} on success.
Returns 401/403 from the require_master_code dependency on failure.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from app.services.limiter import limiter
from app.services.master_code_auth import get_code_credits, require_master_code

router = APIRouter(prefix="/api", tags=["auth"])


@router.get(
    "/auth/ping",
    summary="Validate a Master Code — returns credits on success",
    dependencies=[Depends(require_master_code)],
)
@limiter.limit("10/minute")
def auth_ping(
    request: Request,
    x_master_code: str | None = Header(default=None, alias="X-Master-Code"),
) -> dict:
    credits = get_code_credits(x_master_code or "")
    return {"status": "ok", "credits": credits}
