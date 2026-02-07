import flask
from flask import Blueprint, g
from flask.typing import ResponseReturnValue
from instancer.backend import Challenge
from instancer.config import config

from .challenge import challenge_info, deployment_status

blueprint = Blueprint("challenges", __name__, url_prefix="/challenges")


@blueprint.route("", methods=["GET"])
def challenges() -> ResponseReturnValue:
    if config.rctf_mode and g.session["team_id"] != str(config.admin_team_id):
        return {"status": "not_admin", "msg": "Challenge listing API is disabled."}, 403
    return {
        "status": "ok",
        "challenges": [
            {
                "challenge_info": challenge_info(chall, tags),
                "deployment": deployment_status(chall),
            }
            for chall, tags in Challenge.fetchall(g.session["team_id"])
        ],
    }
