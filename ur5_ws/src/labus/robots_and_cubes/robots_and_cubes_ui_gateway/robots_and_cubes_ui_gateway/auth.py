"""Small server-side authorization boundary for a local exhibition operator."""

from hmac import compare_digest
from typing import Optional

from fastapi import Header, HTTPException, status


class OperatorAuthorizer:
    """Validate a runtime-provided bearer token without storing user accounts."""

    def __init__(self, token: str) -> None:
        if not token or not token.strip():
            raise ValueError('operator authorization token must not be empty')
        self._token = token

    async def require_operator(
        self, authorization: Optional[str] = Header(default=None)
    ) -> None:
        """Reject every operator capability lacking the configured bearer token."""
        prefix = 'Bearer '
        supplied = (
            authorization[len(prefix):]
            if authorization and authorization.startswith(prefix) else ''
        )
        if not compare_digest(supplied, self._token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='operator authorization required',
                headers={'WWW-Authenticate': 'Bearer'},
            )
