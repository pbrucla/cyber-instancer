from flask import Blueprint, g

from instancer.backend import Challenge

blueprint = Blueprint("challenge", __name__, url_prefix="/challenge/<chall_id>")


@blueprint.url_value_preprocessor
def fetch_challenge(endpoint, values):
    """Fetch the challenge ID from the URL."""

    g.chall_id = values.pop("chall_id")


@blueprint.before_request
def check_challenge():
    """Fetch the challenge from the database.

    Return 404 if the challenge ID is invalid.
    """

    chall = Challenge.fetch(g.chall_id, g.session["team_id"])
    if chall is None:
        return {"status": "invalid_chall_id", "msg": "invalid challenge ID"}, 404
    g.chall = chall


@blueprint.route("/deployment", methods=["POST"])
def challenge_deploy():
    return {
        "success": True,
        "id": g.chall_id,
        "connection": ["127.0.0.1:25565"],
        "expiration": 1685602800000,
        "msg": "Successfully deployed/extended challenge",
    }


@blueprint.route("/deployment", methods=["DELETE"])
def cd_terminate():
    return {
        "success": True,
        "id": g.chall_id,
        "msg": "Successfully terminated challenge",
    }


@blueprint.route("/deployment", methods=["GET"])
def cd_get():
    return {
        "id": g.chall_id,
        "name": "Test chall",
        "tags": ["demo", "beginner"],
        "category": "web",
        "deployed": True,
        "connection": ["127.0.0.1:25565"],
    }


@blueprint.route("", methods=["GET"])
def challenge_get():
    """Return challenge info.

    If there is no error, response contains a `challenge_info` object with the ID, name, author, description, and categories.
    """

    return {
        "status": "ok",
        "challenge_info": {
            "id": g.chall_id,
            "name": g.chall.metadata.name,
            "author": g.chall.metadata.author,
            "description": g.chall.metadata.description,
            "categories": g.chall.categories(),
            "tags": g.chall.tags(),
        },
    }
