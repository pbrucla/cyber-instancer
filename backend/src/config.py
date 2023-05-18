from dataclasses import dataclass
import os
from typing import Any, IO, Callable
import yaml
import jsonschema
import redis
from psycopg_pool import ConnectionPool

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


def parse_bool(s: str):
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
class Config:
    secret_key: bytes = None
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


config = Config()
"Server configuration"


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
                "in_cluster": {"type": "boolean"},
                "redis": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "number"},
                        "password": {"type": "string"},
                    },
                },
                "postgres": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "number"},
                        "user": {"type": "string"},
                        "database": {"type": "string"},
                        "password": {"type": "string"},
                    },
                },
                "redis_resync_interval": {"type": "number"},
            },
        },
    )

    apply_dict(c, "secret_key", "secret_key", func=lambda x: x.encode())
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


try:
    user_config = load_dict(try_open(["config.yml", "config.yaml"], "r"))
    apply_config(user_config)
except FileNotFoundError:
    pass

apply_env("INSTANCER_SECRET_KEY", "secret_key", func=lambda x: x.encode())
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

if config.secret_key is None:
    raise ValueError("No secret key was supplied in configuration")

rclient = redis.Redis(
    host=config.redis_host, port=config.redis_port, password=config.redis_password
)
"Redis client"

pg_pool = ConnectionPool(
    kwargs={
        "host": config.postgres_host,
        "dbname": config.postgres_database,
        "user": config.postgres_user,
        "port": config.postgres_port,
        "password": config.postgres_password,
    },
)
"Postgres connection pool"
