import re

import jsonschema
from flask import Blueprint, g, json, request
from flask.typing import ResponseReturnValue
from psycopg.errors import UniqueViolation

from instancer.backend import Challenge, ChallengeMetadata, ChallengeTag
from instancer.config import config

blueprint = Blueprint("admin", __name__)


# @blueprint.route("/challenges/<chall_id>", methods=["GET"])
# def challenge_get(chall_id: str) -> ResponseReturnValue:
#     """Get a challenge by challenge ID & team ID."""

#     try:
#         team_id = request.args["team_id"]
#     except KeyError:
#         return {"status": "missing_team_id", "msg": "Missing team ID"}, 400

#     challenges = []

#     for chall, tags in Challenge.fetchall(team_id):
#         output = chall.json()
#         output["tags"] = tags
#         challenges.append(output)

#     if chall_id == "all":
#         return {"status": "ok", "challenges": Challenge.fetchall(team_id)}

#     chall = Challenge.fetch(chall_id, team_id)
#     if chall is None:
#         return {"status": "invalid_chall_id", "msg": "Invalid challenge ID"}, 404

#     output = chall.json()
#     output["tags"] = ChallengeTag.fetchall(chall_id)
#     challenges.append(output)

#     return {"status": "ok", "challenges": output}


@blueprint.route("/request_info", methods=["GET"])
def request_info() -> ResponseReturnValue:
    """Returns information about a request. Used for debugging"""
    return {"status": "ok", "headers": str(request.headers)}
