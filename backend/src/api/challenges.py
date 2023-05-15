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
        }
    ]
    return flask.jsonify(results=res)
