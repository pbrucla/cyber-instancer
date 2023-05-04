from dataclasses import dataclass, field
import os
from typing import Any, IO
import yaml
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
    challenge_dir: str = os.environ.get("INSTANCER_CHALLENGE_DIR", "./challenges") + "/"
    defaults: dict[str, Any] = field(default_factory=dict)
    challenges: dict[str, ChallengeConfig] = field(default_factory=dict)


config = Config()

user_config = load_dict(
    try_open(
        [
            config.challenge_dir + "instancer.yaml",
            config.challenge_dir + "instancer.yml",
        ],
        "r",
    )
)

if "defaults" in user_config:
    config.defaults = user_config["defaults"]

for td in os.scandir(config.challenge_dir):
    if not td.is_dir():
        continue
    for d in os.scandir(td.path):
        if not d.is_dir():
            continue
        try:
            if d.name.startswith("-") or any(x not in VALID_ID_CHARS for x in d.name):
                raise ValueError("Challenge id must be [a-z0-9][-a-z0-9]*")
            if d.name in config.challenges:
                raise ValueError("Challenge with same id already exists")
            try:
                challenge_config = load_dict(
                    try_open(
                        [
                            os.path.join(d.path, "challenge.yaml"),
                            os.path.join(d.path, "challenge.yml"),
                        ],
                        "r",
                    )
                )
            except FileNotFoundError:
                continue
            

            total_config = config.defaults | challenge_config

            if "deploy" not in total_config:
                continue

            parsed_config = ChallengeConfig(id=d.name, build_path=os.path.join(d.path, total_config["deploy"]))
            config.challenges[d.name] = parsed_config
        except Exception:
            print(f"Got exception when parsing challenge {d.name}:", file=stderr)
            raise

print(config)
