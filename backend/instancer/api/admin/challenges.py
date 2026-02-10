import re

import jsonschema
from flask import Blueprint, json, request
from flask.typing import ResponseReturnValue
from psycopg.errors import UniqueViolation

from instancer.backend import Challenge, ChallengeMetadata, ChallengeTag

blueprint = Blueprint("admin_challenges", __name__, url_prefix="/challenges")


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


@blueprint.route("/<chall_id>", methods=["GET"])
def get_challenge(chall_id: str) -> ResponseReturnValue:
    info = Challenge.fetch_info(chall_id)
    if info is not None:
        return {**{"status": "ok"}, **info.get_json()}
    else:
        return {"status": "not_found", "msg": "Challenge not found"}


@blueprint.route("/create", methods=["POST"])
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
        categories = [x.strip() for x in request.form["categories"].split(",")]
        other_tags = [x.strip() for x in request.form["tags"].split(",")]
        replace_existing = request.form.get("replace_existing", False)
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

    try:
        Challenge.create(chall_id, per_team, cfg, lifetime, boot_time, metadata, tags)
    except UniqueViolation:
        if replace_existing:
            Challenge.delete(chall_id)
            Challenge.create(
                chall_id, per_team, cfg, lifetime, boot_time, metadata, tags
            )
        else:
            return {
                "status": "duplicate_challenge_id",
                "msg": "Challenge already exists, and replace_existing is false or not set.",
            }
        return {"status": "ok", "msg": "Replaced older challenge"}

    return {"status": "ok"}


@blueprint.route("/<chall_id>", methods=["PUT"])
def challenge_update(chall_id: str) -> ResponseReturnValue:
    """Update a challenge."""

    # per team challenges need to be deleted and re-created?
    # per_team = request.form.get("per_team")

    # challenge does not have cfg
    # cfg = request.form.get("cfg")
    try:
        lifetime = request.form.get("lifetime", type=int)
    except ValueError:
        return {"status": "invalid_lifetime", "msg": "lifetime must be a number"}, 400
    name = request.form.get("name")
    description = request.form.get("description")
    author = request.form.get("author")

    categories = request.form.get("categories")
    other_tags = request.form.get("tags")

    if not re.fullmatch(r"[a-z0-9]([-a-z0-9]{,62}[a-z0-9])?", chall_id):
        return {
            "status": "invalid_id",
            "msg": "challenge id must match [a-z0-9]([-a-z0-9]{,62}[a-z0-9]",
        }, 400

    chall = Challenge.fetch(chall_id, "test")
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

    # if cfg is not None:
    #     cfg = json.loads(cfg)

    #     try:
    #         jsonschema.validate(cfg, config_schema)
    #     except jsonschema.ValidationError as e:
    #         return {"status": "invalid_config", "msg": str(e)}, 400

    #     tcp = cfg.get("tcp", {})
    #     http = cfg.get("http", {})

    #     for contname in tcp:
    #         if contname not in cfg["containers"]:
    #             return {
    #                 "status": "invalid_tcp",
    #                 "msg": f"exposed port for non-existent container {contname!r}",
    #             }
    #     for contname in http:
    #         if contname not in cfg["containers"]:
    #             return {
    #                 "status": "invalid_tcp",
    #                 "msg": f"exposed subdomain for non-existent container {contname!r}",
    #             }
    #     for contname, container in cfg["containers"].items():
    #         if not re.fullmatch(r"[a-z0-9]([-a-z0-9]{,62}[a-z0-9])?", contname):
    #             return {
    #                 "status": "invalid_container",
    #                 "msg": f"container id {contname!r} does not match [a-z0-9]([-a-z0-9]{{,62}}[a-z0-9]",
    #             }, 400
    #         if contname.endswith("-instancer-external"):
    #             return {
    #                 "status": "invalid_container",
    #                 "msg": "suffix -instancer-external is reserved and cannot be used for containers",
    #             }, 400
    #         exposed_ports = tcp.get(contname, [])
    #         container_ports = container.get("ports", [])
    #         private_ports = [x for x in container_ports if x not in exposed_ports]
    #         if (
    #             len(exposed_ports) > 0
    #             and len(private_ports) > 0
    #             and not container.get("multiService", False)
    #         ):
    #             return {
    #                 "status": "invalid_container",
    #                 "msg": f"container {contname!r} has both exposed and private ports but multiService is not true",
    #             }, 400

    #     chall.cfg = cfg

    if name is not None:
        chall.metadata.name = name

    if description is not None:
        chall.metadata.description = description

    if author is not None:
        chall.metadata.author = author

    if not (categories is None and other_tags is None):
        new_tags = []
        if categories is not None:
            categories_list = categories.split()
            new_tags += [
                ChallengeTag(category, is_category=True) for category in categories_list
            ]

        if other_tags is not None:
            other_tags_list = other_tags.split()
            new_tags += [
                ChallengeTag(tag, is_category=False) for tag in other_tags_list
            ]

        chall.replace_tags(new_tags)

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
