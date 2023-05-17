import flask

from . import blueprint


@blueprint.route("/api/challenges", methods=["GET"])
def challenges():
    res = [
        {
            "id": "test",
            "name": "Test chall",
            "tags": ["demo", "beginner"],
            "category": "web",
            "deployed": False,
        },
        {
            "id": "test2",
            "name": "Test chall 2",
            "tags": ["demo", "advanced"],
            "category": "pwn",
            "deployed": True,
        },
        {
            "id": "test3",
            "name": "Test chall 3",
            "tags": ["demo", "la ctf 2023"],
            "category": "misc",
            "deployed": False,
        },
    ]
    return flask.jsonify(results=res)
