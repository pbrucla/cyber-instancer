import json
import secrets
from typing import Any

from instancer.config import rclient


def new_session(team_id: str) -> str:
    """Create a new session.

    Returns the session token.
    """

    token = secrets.token_urlsafe()
    rclient.set(f"session:{token}", json.dumps({"team_id": team_id}), ex=7 * 24 * 3600)
    return token


def get_session(token: str) -> dict[str, Any] | None:
    data = rclient.get(f"session:{token}")
    if data is None:
        return None
    return json.loads(data)
