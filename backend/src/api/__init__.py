from flask import Blueprint

blueprint = Blueprint("challenges", __name__)

from . import challenge
from . import challenges
