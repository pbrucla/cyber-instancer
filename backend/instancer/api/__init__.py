from flask import Blueprint

from . import account
from . import challenge
from . import challenges

blueprint = Blueprint("api", __name__)
blueprint.register_blueprint(account.blueprint)
blueprint.register_blueprint(challenge.blueprint, url_prefix="/challenge")
blueprint.register_blueprint(challenges.blueprint, url_prefix="/challenges")
