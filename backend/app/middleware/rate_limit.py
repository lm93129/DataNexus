from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _identity_key_func(request: Request) -> str:
    """按用户身份限流，未认证时按 IP"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from app.core.security import verify_token
        payload = verify_token(auth_header[7:])
        if payload:
            return payload.get("sub", get_remote_address(request))
    return get_remote_address(request)


limiter = Limiter(key_func=_identity_key_func)
