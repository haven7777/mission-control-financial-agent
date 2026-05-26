"""Shared slowapi rate-limiter instance.

Import `limiter` here; attach it to `app.state.limiter` in main.py so
slowapi can inject rate-limit headers into responses.

Key function: real client IP from the ASGI connection scope.  When running
behind a trusted reverse proxy in production, swap `get_remote_address` for
a function that reads `X-Forwarded-For` after validating the proxy is
actually trusted.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
