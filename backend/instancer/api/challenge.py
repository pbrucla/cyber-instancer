from flask import Blueprint, g

from instancer.backend import Challenge

blueprint = Blueprint("challenge", __name__, url_prefix="/challenge/<chall_id>")


@staticmethod
def process_port_mapping(
    port_map: dict[tuple[str, int], int | str]
) -> dict[str, int | str]:
    return {
        "{}:{}".format(container_name, internal_port): external_access
        for (
            (container_name, internal_port),
            external_access,
        ) in g.chall.port_mappings().items()
    }


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
    """
    Starts or renews a team's challenge deployment.
    """
    g.chall.start()
    return {
        "success": True,
        "id": g.chall.id,
        "port_mappings": process_port_mapping(g.chall.port_mappings()),
        "expiration": g.chall.expiration(),
        "msg": "Successfully deployed challenge",
    }


@blueprint.route("/deployment", methods=["DELETE"])
def cd_terminate():
    """
    Terminates a team's challenge deployment.
    """
    g.chall.stop()
    return {
        "success": True,
        "id": g.chall.id,
        "msg": "Successfully terminated challenge",
    }


@blueprint.route("/deployment", methods=["GET"])
def cd_get():
    """
    Return a team's challenge deployment info
    """
    expiration = g.chall.expiration()
    return {
        "status": "ok",
        "deployment": None
        if expiration is None
        else {
            "expiration": expiration,
            "port_mappings": process_port_mapping(g.chall.port_mappings()),
        },
    }


@blueprint.route("", methods=["GET"])
def challenge_get():
    """Return challenge info.

    If there is no error, response contains a `challenge_info` object with the ID, name, author, description, and tags.
    """

    return {
        "status": "ok",
        "challenge_info": {
            "id": g.chall_id,
            "name": g.chall.metadata.name,
            "author": g.chall.metadata.author,
            "description": g.chall.metadata.description,
            "tags": [(tag.name, tag.is_category) for tag in g.chall.tags()],
        },
    }
