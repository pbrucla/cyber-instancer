import json
import secrets
from typing import Any, cast

from instancer.config import config, rclient


def new_session(team_id: str) -> str:
    """Create a new session.

    Returns the session token.
    """

    token = secrets.token_urlsafe()
    rclient.set(
        f"session:{token}", json.dumps({"team_id": team_id}), ex=config.session_length
    )
    return token


def get_session(token: str) -> dict[str, Any] | None:
    """Retrieve session data.

    Returns a dict containing the session data if the token is valid and None otherwise.
    """

    data = rclient.get(f"session:{token}")
    if data is None:
        return None
    return cast(dict[str, Any], json.loads(data))
