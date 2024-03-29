from flask import Blueprint, g, request
from flask.typing import ResponseReturnValue

from instancer.config import config

from . import account, admin, authentication, challenge, challenges

blueprint = Blueprint("api", __name__, url_prefix="/api")
blueprint.register_blueprint(account.blueprint)
blueprint.register_blueprint(challenge.blueprint)
blueprint.register_blueprint(challenges.blueprint)
blueprint.register_blueprint(admin.blueprint)


@blueprint.before_request
def check_authorization() -> ResponseReturnValue | None:
    """Check the client's authentication token and set g.session to the session data."""

    if request.endpoint in [
        "api.account.register",
        "api.account.login",
        "api.account.dev_login",
        "api.account.dev_register",
        "api.account.preview",
    ]:
        return None
    if request.authorization is None:
        return {
            "status": "missing_authorization",
            "msg": "authentication is required",
        }, 401
    if request.authorization.type != "bearer":
        return {
            "status": "unsupported_authorization_type",
            "msg": 'authorization type must be "Bearer"',
        }, 401
    if request.authorization.token is None:
        return {
            "status": "missing_token",
            "msg": "missing session token",
        }
    session = authentication.get_session(request.authorization.token)
    if session is None:
        return {"status": "invalid_token", "msg": "invalid token"}, 401
    g.session = session
    return None


@blueprint.before_request
def rctf_mode() -> ResponseReturnValue | None:
    if not config.rctf_mode:
        return None
    if request.endpoint in ["api.account.register", "api.account.update_profile"]:
        return {"status": "disabled", "msg": "this api endpoint is disabled"}, 405
    else:
        return None
