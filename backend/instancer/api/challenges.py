import flask
from flask import Blueprint, g
from instancer.backend import Challenge

blueprint = Blueprint("challenges", __name__, url_prefix="/challenges")


@blueprint.route("", methods=["GET"])
def challenges():
    challenges = Challenge.fetchall(g.session["team_id"])
    challenges_json = []
    for challenge in challenges:
        id = challenge[0].id
        name = challenge[0].metadata.name
        tags = challenge[1]
        deployed = challenge[0].is_running()
        challenges_json.append({"id": id, "name": name, "tags": tags, "deployed": deployed})

    return challenges_json
