from flask import Blueprint, g
from flask.typing import ResponseReturnValue

from instancer.config import config

from . import admin, challenges

blueprint = Blueprint("admin", __name__, url_prefix="/admin")
blueprint.register_blueprint(admin.blueprint)
blueprint.register_blueprint(challenges.blueprint)


@blueprint.before_request
def check_admin_team() -> ResponseReturnValue | None:
    """Only allow access for the admin team."""

    if g.session["team_id"] != str(config.admin_team_id):
        return {"status": "not_admin", "msg": "only admins can use the admin API"}, 403
    return None
