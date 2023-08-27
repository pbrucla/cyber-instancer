import os
from base64 import b64decode
from dataclasses import asdict, dataclass
from typing import Any, Callable, TextIO
from uuid import UUID

import jsonschema
import psycopg
import redis
import yaml

VALID_ID_CHARS: set[str] = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def try_open(files: list[str]) -> TextIO:
    for f in files:
        try:
            return open(f, "r")
        except FileNotFoundError:
            pass
    raise FileNotFoundError(
        f"Attempted to open files {', '.join(files)} and none existed"
    )


def load_dict(stream: TextIO) -> dict[str, Any]:
    ret = yaml.load(stream, yaml.Loader)
    if not isinstance(ret, dict):
        raise ValueError("Top-level value must be a mapping")
    return ret


def parse_bool(s: str) -> bool:
    if s.lower() in ["y", "yes", "t", "true", "1"]:
        return True
    elif s.lower() in ["n", "no", "f", "false", "0", ""]:
        return False
    raise ValueError(f"Could not parse boolean {s}")


@dataclass
class ChallengeConfig:
    id: str
    build_path: str


@dataclass
class PartialConfig:
    """A possibly incomplete config where required options might be None."""

    login_secret_key: bytes | None = None
    admin_team_id: UUID | None = None
    in_cluster: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str | None = None
    postgres_database: str = "postgres"
    redis_resync_interval: int = 60
    dev: bool = False
    url: str = "http://localhost:8080"
    challenge_host: str = "localhost"
    rctf_mode: bool = False
    rctf_url: str | None = None
    session_length: int = 24 * 3600


@dataclass
class Config(PartialConfig):
    """Instancer configuration."""

    login_secret_key: bytes

    def __init__(self, partial_config: PartialConfig):
        if partial_config.login_secret_key is None:
            raise ValueError("No login secret key was supplied in configuration")
        if len(b64decode(partial_config.login_secret_key)) != 32:
            raise ValueError(
                "Invalid secret login key. Secret login key must be exactly 32 bytes long, base64 encoded"
            )
        super().__init__(**asdict(partial_config))


partial_config = PartialConfig()
"Server configuration"


def apply_dict(
    c: dict[str, Any],
    out_key: str,
    *keys: str,
    func: Callable[[Any], Any] | None = None,
) -> None:
    cur = c
    for k in keys:
        if k not in cur:
            return
        cur = cur[k]
    if func is not None:
        cur = func(cur)
    setattr(partial_config, out_key, cur)


def apply_env(var: str, out_key: str, func: Callable[[Any], Any] | None = None) -> None:
    val = os.environ.get(var)
    if val is None:
        return
    if func is not None:
        val = func(val)
    setattr(partial_config, out_key, val)


def apply_config(c: dict[str, Any]) -> None:
    jsonschema.validate(
        c,
        {
            "type": "object",
            "properties": {
                "login_secret_key": {"type": "string"},
                "admin_team_id": {"type": "string"},
                "in_cluster": {"type": "boolean"},
                "redis": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "password": {"type": "string"},
                    },
                },
                "postgres": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "user": {"type": "string"},
                        "database": {"type": "string"},
                        "password": {"type": "string"},
                    },
                },
                "redis_resync_interval": {"type": "number"},
                "dev": {"type": "boolean"},
                "url": {"type": "string"},
                "challenge_host": {"type": "string"},
                "rctf_mode": {"type": "boolean"},
                "rctf_url": {"type": "string"},
                "session_length": {"type": "integer"},
            },
        },
    )

    apply_dict(c, "login_secret_key", "login_secret_key", func=lambda x: x.encode())
    apply_dict(c, "admin_team_id", "admin_team_id", func=UUID)
    apply_dict(c, "in_cluster", "in_cluster")
    apply_dict(c, "redis_host", "redis", "host")
    apply_dict(c, "redis_port", "redis", "port")
    apply_dict(c, "redis_password", "redis", "password")
    apply_dict(c, "postgres_host", "postgres", "host")
    apply_dict(c, "postgres_port", "postgres", "port")
    apply_dict(c, "postgres_user", "postgres", "user")
    apply_dict(c, "postgres_database", "postgres", "database")
    apply_dict(c, "postgres_password", "postgres", "password")
    apply_dict(c, "redis_resync_interval", "redis_resync_interval")
    apply_dict(c, "dev", "dev")
    apply_dict(c, "url", "url")
    apply_dict(c, "challenge_host", "challenge_host")
    apply_dict(c, "rctf_mode", "rctf_mode")
    apply_dict(c, "session_length", "session_length")
    apply_dict(c, "rctf_url", "rctf_url")


try:
    user_config = load_dict(try_open(["config.yml", "config.yaml"]))
    apply_config(user_config)
except FileNotFoundError:
    pass

apply_env("INSTANCER_LOGIN_SECRET_KEY", "login_secret_key", func=lambda x: x.encode())
apply_env("INSTANCER_ADMIN_TEAM_ID", "admin_team_id", func=UUID)
apply_env("INSTANCER_REDIS_HOST", "redis_host")
apply_env("INSTANCER_REDIS_PORT", "redis_port", func=int)
apply_env("INSTANCER_REDIS_PASSWORD", "redis_password")
apply_env("INSTANCER_IN_CLUSTER", "in_cluster", func=parse_bool)
apply_env("INSTANCER_POSTGRES_HOST", "postgres_host")
apply_env("INSTANCER_POSTGRES_PORT", "postgres_port", func=int)
apply_env("INSTANCER_POSTGRES_USER", "postgres_user")
apply_env("INSTANCER_POSTGRES_DATABASE", "postgres_database")
apply_env("INSTANCER_POSTGRES_PASSWORD", "postgres_password")
apply_env("INSTANCER_REDIS_RESYNC_INTERVAL", "redis_resync_interval", func=int)
apply_env("INSTANCER_DEV", "dev", func=parse_bool)
apply_env("INSTANCER_URL", "url")
apply_env("INSTANCER_CHALLENGE_HOST", "challenge_host")
apply_env("INSTANCER_RCTF_MODE", "rctf_mode", func=parse_bool)
apply_env("INSTANCER_SESSION_LENGTH", "session_length", func=int)
apply_env("INSTANCER_RCTF_URL", "rctf_url")

config = Config(partial_config)

rclient = redis.Redis(
    host=config.redis_host, port=config.redis_port, password=config.redis_password
)
"Redis client"


def connect_pg() -> psycopg.Connection[Any]:
    """Spawn a postgres connection."""
    return psycopg.connect(
        host=config.postgres_host,
        dbname=config.postgres_database,
        user=config.postgres_user,
        port=config.postgres_port,
        password=config.postgres_password,
    )
