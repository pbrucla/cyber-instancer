import flask
from flask import Blueprint, g
from flask.typing import ResponseReturnValue

from instancer.backend import Challenge

from .challenge import challenge_info, deployment_status

blueprint = Blueprint("challenges", __name__, url_prefix="/challenges")


@blueprint.route("", methods=["GET"])
def challenges() -> ResponseReturnValue:
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
