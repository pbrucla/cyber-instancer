import re

import jsonschema
from flask import Blueprint, g, json, request
from flask.typing import ResponseReturnValue

from instancer.backend import Challenge, ChallengeMetadata, ChallengeTag
from instancer.config import config

blueprint = Blueprint("admin", __name__, url_prefix="/admin")

container_schema = {
    "type": "object",
    "required": ["image"],
    "properties": {
        "image": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "command": {"type": "array", "items": {"type": "string"}},
        "imagePullPolicy": {"type": "string"},
        "stdin": {"type": "boolean"},
        "stdinOnce": {"type": "boolean"},
        "terminationMessagePath": {"type": "string"},
        "terminationMessagePolicy": {"type": "string"},
        "tty": {"type": "boolean"},
        "workingDir": {"type": "string"},
        "env": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "value"],
                "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
            },
        },
        "environment": {"type": "object", "additionalProperties": {"type": "string"}},
        "kubePorts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["containerPort"],
                "properties": {
                    "containerPort": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 65535,
                    },
                    "hostIP": {"type": "string"},
                    "hostPort": {"type": "integer", "minimum": 1, "maximum": 65535},
                    "name": {"type": "string"},
                    "protocol": {"enum": ["UDP", "TCP", "SCTP"]},
                },
            },
        },
        "ports": {
            "type": "array",
            "items": {"type": "integer", "minimum": 1, "maximum": 65535},
        },
        # not as validated as it could be
        "securityContext": {
            "type": "object",
            "properties": {
                "runAsUser": {"type": "integer"},
                "runAsNonRoot": {"type": "boolean"},
                "runAsGroup": {"type": "integer"},
                "readOnlyRootFilesystem": {"type": "boolean"},
                "procMount": {"type": "string"},
                "privileged": {"type": "boolean"},
                "allowPrivilegeEscalation": {"type": "boolean"},
            },
        },
        "resources": {
            "type": "object",
            "properties": {
                "limits": {
                    "type": "object",
                    "properties": {
                        "limits": {"type": "string"},
                        "memory": {"type": "string"},
                    },
                },
                "requests": {
                    "type": "object",
                    "properties": {
                        "limits": {"type": "string"},
                        "memory": {"type": "string"},
                    },
                },
            },
        },
        "hasEgress": {"type": "boolean"},
        "multiService": {"type": "boolean"},
    },
    "additionalProperties": False,
}

config_schema = {
    "type": "object",
    "required": ["containers"],
    "properties": {
        "containers": {"type": "object", "additionalProperties": container_schema},
        "tcp": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1, "maximum": 65535},
            },
        },
        "http": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {
                    "type": "array",
                    "prefixItems": [
                        {"type": "integer", "minimum": 1, "maximum": 65535},
                        {"type": "string"},
                    ],
                    "items": False,
                },
            },
        },
    },
}


@blueprint.before_request
def check_admin_team() -> ResponseReturnValue | None:
    """Only allow access for the admin team."""

    if g.session["team_id"] != str(config.admin_team_id):
        return {"status": "not_admin", "msg": "only admins can use the admin API"}, 403
    return None


@blueprint.route("/challenges/<chall_id>", methods=["GET"])
def challenge_get(chall_id: str) -> ResponseReturnValue:
    """Get a challenge by challenge ID & team ID."""

    try:
        team_id = request.args["team_id"]
    except KeyError:
        return {"status": "missing_team_id", "msg": "Missing team ID"}, 400

    challenges = []

    for chall, tags in Challenge.fetchall(team_id):
        output = chall.json()
        output["tags"] = tags
        challenges.append(output)

    if chall_id == "all":
        return {"status": "ok", "challenges": Challenge.fetchall(team_id)}

    chall = Challenge.fetch(chall_id, team_id)
    if chall is None:
        return {"status": "invalid_chall_id", "msg": "Invalid challenge ID"}, 404

    output = chall.json()
    output["tags"] = ChallengeTag.fetchall(chall_id)
    challenges.append(output)

    return {"status": "ok", "challenges": output}


@blueprint.route("/challenges/upload", methods=["POST"])
def challenge_upload() -> ResponseReturnValue:
    """Create a new challenge."""

    try:
        chall_id = request.form["chall_id"]
        per_team = (
            request.form.get("per_team") == "true"
            or request.form.get("per_team") == "True"
        )
        cfg = json.loads(request.form["cfg"])
        lifetime = int(request.form["lifetime"])
        boot_time = int(request.form["boot_time"])
        metadata = ChallengeMetadata(
            name=request.form["name"],
            description=request.form["description"],
            author=request.form["author"],
        )
        categories = request.form["categories"].split()
        other_tags = request.form["tags"].split()
    except (KeyError, ValueError):
        return {"status": "invalid_request", "msg": "invalid request"}, 400
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9]{,62}[a-z0-9])?", chall_id):
        return {
            "status": "invalid_id",
            "msg": "challenge id must match [a-z0-9]([-a-z0-9]{,62}[a-z0-9]",
        }, 400
    if lifetime <= 0:
        return {"status": "invalid_lifetime", "msg": "lifetime must be positive"}, 400
    if boot_time < 0 or boot_time >= lifetime:
        return {
            "status": "invalid_boot_time",
            "msg": "boot_time must be positive but less than the challenge lifetime",
        }, 400

    try:
        jsonschema.validate(cfg, config_schema)
    except jsonschema.ValidationError as e:
        return {"status": "invalid_config", "msg": str(e)}, 400

    tcp = cfg.get("tcp", {})
    http = cfg.get("http", {})

    for contname in tcp:
        if contname not in cfg["containers"]:
            return {
                "status": "invalid_tcp",
                "msg": f"exposed port for non-existent container {contname!r}",
            }
    for contname in http:
        if contname not in cfg["containers"]:
            return {
                "status": "invalid_tcp",
                "msg": f"exposed subdomain for non-existent container {contname!r}",
            }
    for contname, container in cfg["containers"].items():
        if not re.fullmatch(r"[a-z0-9]([-a-z0-9]{,62}[a-z0-9])?", contname):
            return {
                "status": "invalid_container",
                "msg": f"container id {contname!r} does not match [a-z0-9]([-a-z0-9]{{,62}}[a-z0-9]",
            }, 400
        if contname.endswith("-instancer-external"):
            return {
                "status": "invalid_container",
                "msg": "suffix -instancer-external is reserved and cannot be used for containers",
            }, 400
        exposed_ports = tcp.get(contname, [])
        container_ports = container.get("ports", [])
        private_ports = [x for x in container_ports if x not in exposed_ports]
        if (
            len(exposed_ports) > 0
            and len(private_ports) > 0
            and not container.get("multiService", False)
        ):
            return {
                "status": "invalid_container",
                "msg": f"container {contname!r} has both exposed and private ports but multiService is not true",
            }, 400

    tags = [ChallengeTag(category, is_category=True) for category in categories] + [
        ChallengeTag(tag, is_category=False) for tag in other_tags
    ]
    Challenge.create(chall_id, per_team, cfg, lifetime, boot_time, metadata, tags)
    return {"status": "ok"}


@blueprint.route("/challenges/<chall_id>", methods=["PUT"])
def challenge_update(chall_id: str) -> ResponseReturnValue:
    """Update a challenge."""

    # per team challenges need to be deleted and re-created?
    # per_team = request.form.get("per_team")
    cfg = request.form.get("cfg")
    lifetime = request.form.get("lifetime")
    name = request.form.get("name")
    description = request.form.get("description")
    author = request.form.get("author")
    # TO DO: unsure about how to handle updating tags
    # categories = request.form.get("categories")
    # other_tags = request.form.get("tags")

    if not re.fullmatch(r"[a-z0-9]([-a-z0-9]{,62}[a-z0-9])?", chall_id):
        return {
            "status": "invalid_id",
            "msg": "challenge id must match [a-z0-9]([-a-z0-9]{,62}[a-z0-9]",
        }, 400

    chall = Challenge.fetch(chall_id)
    if chall is None:
        return {"status": "invalid_chall_id", "msg": "invalid challenge ID"}, 404

    if lifetime is not None:
        lifetime = int(lifetime)

        if lifetime <= 0:
            return {
                "status": "invalid_lifetime",
                "msg": "lifetime must be positive",
            }, 400

        chall.lifetime = lifetime

    if cfg is not None:
        cfg = json.loads(cfg)

        try:
            jsonschema.validate(cfg, config_schema)
        except jsonschema.ValidationError as e:
            return {"status": "invalid_config", "msg": str(e)}, 400

        tcp = cfg.get("tcp", {})
        http = cfg.get("http", {})

        for contname in tcp:
            if contname not in cfg["containers"]:
                return {
                    "status": "invalid_tcp",
                    "msg": f"exposed port for non-existent container {contname!r}",
                }
        for contname in http:
            if contname not in cfg["containers"]:
                return {
                    "status": "invalid_tcp",
                    "msg": f"exposed subdomain for non-existent container {contname!r}",
                }
        for contname, container in cfg["containers"].items():
            if not re.fullmatch(r"[a-z0-9]([-a-z0-9]{,62}[a-z0-9])?", contname):
                return {
                    "status": "invalid_container",
                    "msg": f"container id {contname!r} does not match [a-z0-9]([-a-z0-9]{{,62}}[a-z0-9]",
                }, 400
            if contname.endswith("-instancer-external"):
                return {
                    "status": "invalid_container",
                    "msg": "suffix -instancer-external is reserved and cannot be used for containers",
                }, 400
            exposed_ports = tcp.get(contname, [])
            container_ports = container.get("ports", [])
            private_ports = [x for x in container_ports if x not in exposed_ports]
            if (
                len(exposed_ports) > 0
                and len(private_ports) > 0
                and not container.get("multiService", False)
            ):
                return {
                    "status": "invalid_container",
                    "msg": f"container {contname!r} has both exposed and private ports but multiService is not true",
                }, 400

        chall.cfg = cfg

    if name is not None:
        chall.metadata.name = name

    if description is not None:
        chall.metadata.description = description

    if author is not None:
        chall.metadata.author = author

    # if categories is not None:
    #     categories = categories.split()

    # if other_tags is not None:
    #     other_tags = other_tags.split()

    # if categories is not None or other_tags is not None:
    #     chall.tags = [ChallengeTag(category, is_category=True) for category in categories] + [
    #         ChallengeTag(tag, is_category=False) for tag in other_tags
    #     ]

    chall.update()

    return {"status": "ok"}


@blueprint.route("/challenges/<chall_id>", methods=["DELETE"])
def challenge_delete(chall_id: str) -> ResponseReturnValue:
    """Delete a challenge."""

    return (
        {"status": "ok"}
        if Challenge.delete(chall_id)
        else ({"status": "invalid_chall_id", "msg": "invalid challenge ID"}, 400)
    )


@blueprint.route("/request_info", methods=["GET"])
def request_info() -> ResponseReturnValue:
    """Returns information about a request. Used for debugging"""
    return {"status": "ok", "headers": str(request.headers)}
