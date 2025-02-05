import re

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from psycopg.errors import UniqueViolation

from instancer.backend import Challenge, ChallengeTag

blueprint = Blueprint("admin_challenge", __name__, url_prefix="/challenge")


from typing import Any

from flask import Blueprint, g, request
from flask.typing import ResponseReturnValue

from instancer.backend import Challenge, ChallengeTag, ResourceUnavailableError
from instancer.config import config


def deployment_status(chall: Challenge) -> dict[str, Any] | None:
    """Return a dict with the challenge deployment status or None if the challenge is not deployed."""

    status = chall.deployment_status()
    if status is None:
        return None
    return {
        "expiration": status.expiration,
        "start_delay": status.start_timestamp,
        "port_mappings": {
            f"{container}:{internal}": external
            for (
                container,
                internal,
            ), external in status.port_mappings.items()
        },
        "host": config.challenge_host,
    }


def challenge_info(chall: Challenge, tags: list[ChallengeTag]) -> dict[str, Any]:
    """Return a dict with the challenge info."""

    return {
        "id": chall.id,
        "name": chall.metadata.name,
        "author": chall.metadata.author,
        "description": chall.metadata.description,
        "tags": [{"name": tag.name, "is_category": tag.is_category} for tag in tags],
        "is_shared": chall.is_shared(),
    }


blueprint = Blueprint("challenge", __name__, url_prefix="/challenge/<chall_id>")


@blueprint.url_value_preprocessor
def fetch_challenge(endpoint: str | None, values: dict[str, str] | None) -> None:
    """Fetch the challenge ID from the URL."""

    # I don't know why this would be None but Flask typing marks it as optional
    if values is not None:
        g.chall_id = values.pop("chall_id")


@blueprint.before_request
def check_challenge() -> ResponseReturnValue | None:
    """Fetch the challenge from the database.

    Return 404 if the challenge ID is invalid.
    """
    if request.args.get("team_id"):
        chall = Challenge.fetch(g.chall_id, request.args.get("team_id"))
    else:
        chall = Challenge.fetch(g.chall_id, g.session["team_id"])
    if chall is None:
        return {"status": "invalid_chall_id", "msg": "invalid challenge ID"}, 404
    g.chall = chall
    return None


@blueprint.route("/deploy", methods=["POST"])
def challenge_deploy() -> ResponseReturnValue:
    """
    Starts or renews a team's challenge deployment.
    """

    try:
        g.chall.start()
    except ResourceUnavailableError:
        return {
            "status": "temporarily_unavailable",
            "msg": "This challenge is temporarily unavailable. Try again in a few moments.",
        }, 503
    except Exception as e:
        print("ERROR when deploying challenge:", e, flush=True)
        return {
            "status": "unknown_error",
            "msg": "An error occurred: " + str(e),
        }, 500

    return {
        "status": "ok",
        "deployment": deployment_status(g.chall),
    }


@blueprint.route("/deployment", methods=["DELETE"])
def cd_terminate() -> ResponseReturnValue:
    """
    Terminates a team's challenge deployment.
    """
    g.chall.stop()
    return {
        "status": "ok",
        "msg": "Successfully terminated challenge",
    }


@blueprint.route("/deployment", methods=["GET"])
def cd_get() -> ResponseReturnValue:
    """
    Return a team's challenge deployment info
    """
    return {
        "status": "ok",
        "deployment": deployment_status(g.chall),
    }


@blueprint.route("", methods=["GET"])
def challenge_get() -> ResponseReturnValue:
    """Return challenge info.

    If there is no error, response contains a `challenge_info` object with the ID, name, author, description, and tags.
    """

    return {
        "status": "ok",
        "challenge_info": challenge_info(g.chall, g.chall.tags()),
    }
