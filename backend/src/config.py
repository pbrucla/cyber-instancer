from dataclasses import dataclass, field
import os
from typing import Any, IO, Callable, TypeVar
import yaml
import jsonschema
from sys import stderr

VALID_ID_CHARS: set[str] = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def try_open(files: list[str], mode: str) -> IO:
    for f in files:
        try:
            return open(f, mode)
        except FileNotFoundError:
            pass
    raise FileNotFoundError(
        f"Attempted to open files {', '.join(files)} and none existed"
    )


def load_dict(stream: Any) -> dict:
    ret = yaml.load(stream, yaml.Loader)
    if not isinstance(ret, dict):
        raise ValueError("Top-level value must be a mapping")
    return ret


@dataclass
class ChallengeConfig:
    id: str
    build_path: str


@dataclass
class Config:
    secret_key: bytes = None
    docker_registry: str = "docker.io"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None


config = Config()


def apply_dict(c: dict, out_key: str, *keys: str, func: Callable = None):
    cur = c
    for k in keys:
        if k not in cur:
            return
        cur = cur[k]
    if func is not None:
        cur = func(cur)
    setattr(config, out_key, cur)

def apply_env(var: Any, out_key: str, func: Callable = None):
    val = os.environ.get(var)
    if val is None:
        return
    if func is not None:
        val = func(val)
    setattr(config, out_key, val)


def apply_config(c: dict):
    jsonschema.validate(
        c,
        {
            "type": "object",
            "properties": {
                "secret_key": {"type": "string"},
                "docker_registry": {"type": "string"},
                "redis": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "number"},
                        "password": {"type": "string"},
                    },
                },
            },
        },
    )

    apply_dict(c, "secret_key", "secret_key", func=lambda x: x.encode())
    apply_dict(c, "docker_registry", "docker_registry")
    apply_dict(c, "redis_host", "redis", "host")
    apply_dict(c, "redis_port", "redis", "port")
    apply_dict(c, "redis_password", "redis", "password")


try:
    user_config = load_dict(try_open(["config.yml", "config.yaml"], "r"))
    apply_config(user_config)
except FileNotFoundError:
    pass

apply_env("INSTANCER_SECRET_KEY", "secret_key", func=lambda x: x.encode())
apply_env("INSTANCER_DOCKER_REGISTRY", "docker_registry")
apply_env("INSTANCER_REDIS_HOST", "redis_host")
apply_env("INSTANCER_REDIS_PORT", "redis_port", func=int)
apply_env("INSTANCER_REDIS_PASSWORD", "redis_password")

if config.secret_key is None:
    raise ValueError("No secret key was supplied in configuration")
