from flask import Blueprint, g, json, request

from instancer.backend import Challenge, ChallengeMetadata, ChallengeTag
from instancer.config import config

blueprint = Blueprint("admin", __name__, url_prefix="/admin")


@blueprint.before_request
def check_admin_team():
    """Only allow access for the admin team."""

    if g.session["team_id"] != str(config.admin_team_id):
        return {"status": "not_admin", "msg": "only admins can use the admin API"}, 403


@blueprint.route("/challenges/upload", methods=["POST"])
def challenge_upload():
    """Create a new challenge."""

    try:
        chall_id = request.form["chall_id"]
        per_team = "per_team" in request.form
        cfg = json.loads(request.form["cfg"])
        lifetime = int(request.form["lifetime"])
        metadata = ChallengeMetadata(
            name=request.form["name"],
            description=request.form["description"],
            author=request.form["author"],
        )
        categories = request.form["categories"].split()
        other_tags = request.form["tags"].split()
    except (KeyError, ValueError):
        return {"status": "invalid_request", "msg": "invalid request"}, 400
    tags = [ChallengeTag(category, is_category=True) for category in categories] + [
        ChallengeTag(tag, is_category=False) for tag in other_tags
    ]
    Challenge.create(chall_id, per_team, cfg, lifetime, metadata, tags)
    return {"status": "ok"}
