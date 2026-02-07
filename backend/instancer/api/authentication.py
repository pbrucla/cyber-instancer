import json
import secrets
from typing import Any, cast

import requests

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


def del_session(token: str) -> bool:
    """Delete session data.

    Returns True if the session was deleted and False otherwise.
    """

    return rclient.delete(f"session:{token}") == 1


def verify_captcha_token(token: str | None) -> bool:
    """Verifies captcha token via Google re-captcha

    Returns True if verified and False otherwise
    If recaptcha is not configured, returns True (bypasses verification)
    """
    # If recaptcha is not configured, bypass verification
    if config.recaptcha_secret is None:
        return True

    if token is None:
        return False

    try:
        payload = {"secret": config.recaptcha_secret, "response": token}
        res = requests.post(
            f"https://www.google.com/recaptcha/api/siteverify", data=payload
        ).json()

        success: bool = res["success"]
        return success
    except (KeyError, requests.JSONDecodeError):
        return False
