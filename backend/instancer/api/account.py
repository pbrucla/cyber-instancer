import flask
from flask import Blueprint, request, session

from instancer.config import config

blueprint = Blueprint("account", __name__)

if config.dev:

    @blueprint.route("/dev_login", methods=["POST"])
    def dev_login():
        try:
            session["team_id"] = request.form["team_id"]
        except KeyError:
            return {"status": "error", "error": "missing team id"}, 400
        return {"status": "ok"}
