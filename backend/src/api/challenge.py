import flask

from . import blueprint


@blueprint.route("/api/challenge/<string:challID>/deploy", methods=["POST"])
def challenge_deploy(challID):
    return {
        "success": True,
        "id": challID,
        "connection": "127.0.0.1:25565",
        "expiration": "1685602800000",
        "msg": "Successfully deployed challenge",
    }


@blueprint.route("/api/challenge/<string:challID>/deployment/extend", methods=["POST"])
def cd_extend(challID):
    return {
        "success": True,
        "id": challID,
        "expiration": 1685602800,
        "msg": "Successfully extended challenge expiration",
    }


@blueprint.route("/api/challenge/<string:challID>/deployment", methods=["DELETE"])
def cd_terminate(challID):
    return {"success": True, "id": challID, "msg": "Successfully terminated challenge"}


@blueprint.route("/api/challenge/<string:challID>/deployment", methods=["GET"])
def cd_get(challID):
    return {
        "id": challID,
        "name": "Test chall",
        "tags": ["demo", "beginner"],
        "category": "web",
        "deployed": True,
        "connection": "127.0.0.1:25565",
    }


@blueprint.route("/api/challenge/<string:challID>", methods=["GET"])
def challenge_get(challID):
    return {
        "id": challID,
        "name": "Test chall",
        "tags": ["demo", "beginner"],
        "category": "web",
    }
