import flask
from flask import Blueprint, request

from . import authentication
from instancer.config import config

blueprint = Blueprint("account", __name__)

if config.dev:

    @blueprint.route("/dev_login", methods=["POST"])
    def dev_login():
        """Login without validating token.

        For development only.
        """

        try:
            team_id = request.form["team_id"]
        except KeyError:
            return {"status": "error", "msg": "missing team ID"}, 400
        return {"status": "ok", "token": authentication.new_session(team_id)}
