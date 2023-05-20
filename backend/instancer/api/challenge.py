from flask import Blueprint, g

from instancer.backend import Challenge

blueprint = Blueprint("challenge", __name__)


@blueprint.route("/<string:chall_id>/deployment", methods=["POST"])
def challenge_deploy(chall_id):
    return {
        "success": True,
        "id": chall_id,
        "connection": ["127.0.0.1:25565"],
        "expiration": 1685602800000,
        "msg": "Successfully deployed/extended challenge",
    }


@blueprint.route("/<string:chall_id>/deployment", methods=["DELETE"])
def cd_terminate(chall_id):
    return {"success": True, "id": chall_id, "msg": "Successfully terminated challenge"}


@blueprint.route("/<string:chall_id>/deployment", methods=["GET"])
def cd_get(chall_id):
    return {
        "id": chall_id,
        "name": "Test chall",
        "tags": ["demo", "beginner"],
        "category": "web",
        "deployed": True,
        "connection": ["127.0.0.1:25565"],
    }


@blueprint.route("/<string:chall_id>", methods=["GET"])
def challenge_get(chall_id):
    chall = Challenge.fetch(chall_id, g.session["team_id"])
    if chall is None:
        return {"status": "error", "msg": "invalid challenge ID"}, 404
    return {
        "status": "ok",
        "challenge_info": {
            "id": chall_id,
            "name": chall.metadata.name,
            "author": chall.metadata.author,
            "description": chall.metadata.description,
            "categories": chall.categories,
            "tags": chall.tags,
        },
    }
