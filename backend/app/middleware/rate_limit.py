"""
Rate limiting via slowapi (limits per IP address).
Attach to FastAPI app via app.state.limiter and the RateLimitExceeded handler.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
