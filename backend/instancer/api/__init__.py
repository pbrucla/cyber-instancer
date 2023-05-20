from flask import Blueprint

from . import challenge
from . import challenges

blueprint = Blueprint("api", __name__)
blueprint.register_blueprint(challenge.blueprint)
blueprint.register_blueprint(challenges.blueprint)
