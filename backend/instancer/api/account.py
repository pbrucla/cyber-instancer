import json
import re
import secrets
import time
import urllib.parse
import uuid

# Login token handling
from base64 import b64decode, b64encode
from dataclasses import dataclass
from typing import Any, Self, cast
from uuid import uuid4

from Crypto.Cipher import AES
from flask import Blueprint, g, request
from flask.typing import ResponseReturnValue
from psycopg.errors import IntegrityError

from instancer.config import config, connect_pg

from . import authentication

blueprint = Blueprint("account", __name__, url_prefix="/accounts")

# Simple dict to map teams table column names to regular names
teams_real_names = {"team_username": "username", "team_email": "email"}


class LoginToken:
    login_token = None

    def __init__(
        self,
        team_id: str,
        timestamp: float | None = None,
        forceUUID: bool = True,
        team_name: str | None = None,
        team_email: str | None = None,
    ):
        """Initialize a LoginToken given decoded parameters"""

        if timestamp is None:
            timestamp = time.time()
        # Unless forceUUID is disabled, all team_ids should be UUIDs
        if (
            re.match(
                r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                team_id,
            )
            is None
        ):
            if forceUUID:
                raise ValueError("A non-UUID was passed in as the team_id")
        self.team_id = team_id
        self.timestamp = timestamp
        self.team_name = team_name
        self.team_email = team_email

    @classmethod
    def decode(cls, token: str) -> Self:
        """Decodes a token

        May throw a ValueError if the key format is invalid"""

        decoded = json.loads(LoginToken.decrypt(token))

        try:
            if decoded["k"] == 8:
                return cls(
                    decoded["d"]["teamId"],
                    timestamp=decoded["t"],
                    team_name=decoded["d"]["name"],
                    team_email=decoded["d"]["email"],
                )
            elif decoded["k"] == 16:
                return cls(decoded["d"], timestamp=decoded["t"])
            else:
                raise ValueError(
                    "Token was an invalid or unknown type (type {})".format(
                        decoded["k"]
                    )
                )
        except KeyError:
            raise ValueError(
                "Invalid key - either it failed to decrypt or was not of the required format or key type"
            )

    def get_login_url(self, currentTime: bool = True, url: str = config.url) -> str:
        return "{}/login?token={}".format(
            url, urllib.parse.quote_plus(self.get_token(currentTime=currentTime))
        )

    def get_token(self, currentTime: bool = True) -> str:
        login_token = {
            "k": 8,
            "t": (int(time.time()) if currentTime else self.timestamp),
            "d": self.team_id,
        }
        encrypted_token = self.encrypt(json.dumps(login_token, separators=(",", ":")))
        return encrypted_token

    @staticmethod
    def decrypt(token: str) -> str:
        """
        Given a base64 string, decrypts using the login secret key

        May raise a ValueError, meaning decryption either failed or message integrity check failed
        """
        key = b64decode(config.login_secret_key)
        data = b64decode(token.encode())
        cipher = AES.new(key, AES.MODE_GCM, data[:12])
        dec = cipher.decrypt_and_verify(data[12:-16], data[-16:])
        return dec.decode("utf-8")

    @staticmethod
    def encrypt(json: str) -> str:
        """
        Given any string (usually json string), encrypts using the login secret key
        """
        key = b64decode(config.login_secret_key)
        dec = str(json).encode()
        nonce = secrets.token_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce)
        enc, mac = cipher.encrypt_and_digest(dec)
        return b64encode(nonce + enc + mac).decode("utf-8")


@dataclass
class TeamAccount:
    """A Team Account"""

    team_id: uuid.UUID
    "The team id"
    team_username: str | None
    "The team's username"
    team_email: str | None
    "The team's email"


def get_all_accounts() -> list[TeamAccount]:
    with connect_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM teams")
            res = cur.fetchall()
    return [TeamAccount(r[0], r[1], r[2]) for r in res]


def find_account(team_id: str) -> TeamAccount | None:
    # in rctf mode, database teams is not used
    if config.rctf_mode:
        return TeamAccount(uuid.UUID(team_id), None, None)
    with connect_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM teams where team_id = %s", (team_id,))
            res = cur.fetchone()
            if res is None:
                return None
            return TeamAccount(res[0], res[1], res[2])


def find_or_create_account(team_id: str) -> TeamAccount:
    if config.rctf_mode:
        # in rctf mode, database teams is not used
        return TeamAccount(uuid.UUID(team_id), None, None)
    with connect_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM teams where team_id = %s", (team_id,))
            res = cur.fetchone()
            if res is None:
                cur.execute(
                    "INSERT INTO teams (team_id, team_username, team_email) VALUES (%s, NULL, NULL)",
                    (team_id,),
                )
                conn.commit()

                return TeamAccount(uuid.UUID(team_id), None, None)
            else:
                return TeamAccount(res[0], res[1], res[2])


def validate_email(email: str) -> bool:
    return (
        re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None
    )


def validate_team_username(team_id: str) -> bool:
    return 3 <= len(team_id) <= 100


@blueprint.route("/register", methods=["POST"])
def register() -> ResponseReturnValue:
    """Register an account

    Requires username, email body parameters
    """
    try:
        team_username = request.form["username"]
    except KeyError:
        return {"status": "missing_username", "msg": "missing username"}, 400
    try:
        email = request.form["email"]
    except KeyError:
        return {"status": "missing_email", "msg": "missing email"}, 400
    if not validate_team_username(team_username):
        return {
            "status": "invalid_username",
            "msg": "Invalid username: must be between 3 and 100 characters",
        }, 400
    if not validate_email(email):
        return {"status": "invalid_email", "msg": "invalid email"}, 400
    team_id = uuid4()

    with connect_pg() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO teams (team_id, team_username, team_email) VALUES (%s, %s, %s)",
                    (team_id, team_username, email),
                )
            except IntegrityError as e:
                conn.rollback()
                failed_key_match = re.match(
                    r"^Key \((.+)\)=", str(e.diag.message_detail)
                )
                if failed_key_match is None:
                    return {
                        "status": "unexpected_error",
                        "msg": "An unexpected error occurred",
                    }, 400
                bad_field = teams_real_names[failed_key_match.group(1)]
                return {
                    "status": "{}_already_taken".format(bad_field),
                    "msg": "{} already taken".format(bad_field),
                }, 400
            conn.commit()
            return {
                "success": True,
                "token": authentication.new_session(str(team_id)),
            }


@blueprint.route("/profile", methods=["GET"])
def profile() -> ResponseReturnValue:
    """Returns profile information

    for now, returns team username, team email, and login url"""

    acc = find_or_create_account(g.session["team_id"])
    username = acc.team_username
    email = acc.team_email

    t = LoginToken(g.session["team_id"])
    return {
        "status": "ok",
        "username": username,
        "email": email,
        "login_url": "Login via the platform"
        if config.rctf_mode
        else t.get_login_url(),
    }


@blueprint.route("/profile", methods=["PATCH"])
def update_profile() -> ResponseReturnValue:
    """Updates information in the profile (email, team name)

    Body fields: neither, one, or both of username, email"""
    with connect_pg() as conn:
        with conn.cursor() as cur:
            # Verify user exists, and if not, create it
            find_or_create_account(g.session["team_id"])
            try:
                if "username" in request.form:
                    if validate_team_username(request.form["username"]):
                        cur.execute(
                            "UPDATE teams SET team_username = %s WHERE team_id = %s",
                            (request.form["username"], g.session["team_id"]),
                        )
                    else:
                        conn.rollback()
                        return {
                            "status": "invalid_username",
                            "msg": "Invalid new username: must be between 3 and 100 characters",
                        }, 400
                if "email" in request.form:
                    if validate_email(request.form["email"]):
                        cur.execute(
                            "UPDATE teams SET team_email = %s WHERE team_id = %s",
                            (request.form["email"], g.session["team_id"]),
                        )
                    else:
                        conn.rollback()
                        return {
                            "status": "invalid_email",
                            "msg": "Invalid new email",
                        }, 400
            except IntegrityError as e:
                conn.rollback()
                failed_key_match = re.match(
                    r"^Key \((.+)\)=", str(e.diag.message_detail)
                )
                if failed_key_match is None:
                    return {
                        "status": "unexpected_error",
                        "msg": "An unexpected error occurred",
                    }, 400
                bad_field = teams_real_names[failed_key_match.group(1)]
                return {
                    "status": "{}_already_taken".format(bad_field),
                    "msg": "{} already taken".format(bad_field),
                }, 400
            conn.commit()
    return {"status": "ok", "msg": "Successfully updated profile"}


@blueprint.route("/login", methods=["POST"])
def login() -> ResponseReturnValue:
    """Allows users to login using login urls

    Requires body param login_token"""
    try:
        token = request.form["login_token"]
    except KeyError:
        return {"status": "missing_login_token", "msg": "Missing login token"}, 401
    try:
        account = LoginToken.decode(token)
    except ValueError:
        return {"status": "invalid_login_token", "msg": "Invalid login token"}, 401

    find_or_create_account(account.team_id)
    return {
        "status": "ok",
        "token": authentication.new_session(account.team_id),
        "msg": "Successfully logged in",
    }


@blueprint.route("/preview", methods=["GET"])
def preview() -> ResponseReturnValue:
    """Decodes a token, returning the embedded team name if one exists"""
    try:
        token = request.args["login_token"]
    except KeyError:
        return {"status": "missing_login_token", "msg": "Missing login token"}, 401
    try:
        account = LoginToken.decode(token)
    except ValueError as e:
        return {
            "status": "invalid_login_token",
            "msg": "Invalid login token",
        }, 401

    return {"status": "ok", "team_name": account.team_name}


if config.dev:

    @blueprint.route("/dev_login", methods=["POST"])
    def dev_login() -> ResponseReturnValue:
        """Force login as specific team_id

        For development only; passing in non-uuids may cause unintended behavior.
        Use /register instead for all normal usage.
        """

        try:
            team_id = request.form["team_id"]
        except KeyError:
            return {"status": "missing_team_id", "msg": "missing team ID"}, 400
        return {"status": "ok", "token": authentication.new_session(team_id)}

    @blueprint.route("/dev_register", methods=["POST"])
    def dev_register() -> ResponseReturnValue:
        """
        Generates a random account and returns a login token

        Used for development purposes especially while in rctf/registrationless mode
        """
        token = LoginToken(str(uuid4()))
        return {
            "status": "ok",
            "token": token.get_token(),
            "login_url": token.get_login_url(),
        }
