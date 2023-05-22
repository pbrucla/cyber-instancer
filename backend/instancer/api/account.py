from psycopg.errors import IntegrityError
from flask import Blueprint, request, g
import re
from . import authentication
from instancer.config import config, connect_pg
from uuid import uuid4
import time
import json
import urllib.parse

blueprint = Blueprint("account", __name__, url_prefix="/accounts")

# Login token handling
from base64 import b64decode, b64encode
from Crypto.Cipher import AES
import secrets


class LoginToken:
    def __init__(self, team_id: str, timestamp=time.time(), forceUUID=True):
        """Initialize a LoginToken given decoded parameters"""

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

    @classmethod
    def decode(cls, token, onlyAllowType8=True):
        decoded = json.loads(LoginToken.decrypt(token))
        if decoded["j"] != 8:
            raise ValueError("Token was an invalid type (type {})".format(decoded["j"]))
        return cls(decoded["d"], timestamp=decoded["t"])

    def get_login_url(self, currentTime=True) -> str:
        return "{}/login?token={}".format(
            config.url, urllib.parse.quote_plus(self.get_token(currentTime=currentTime))
        )

    def get_token(self, currentTime=True):
        login_token = {
            "k": 8,
            "t": (int(time.time()) if currentTime else self.timestamp),
            "d": self.team_id,
        }
        encrypted_token = LoginToken.encrypt(
            json.dumps(login_token, separators=(",", ":"))
        )
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


def validate_email(email: str) -> bool:
    return (
        re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None
    )


def validate_team_username(team_id: str) -> bool:
    return 3 <= len(team_id) <= 100


@blueprint.route("/register", methods=["POST"])
def register():
    """Register an account

    Requires team_username, email body parameters
    """
    try:
        team_username = request.form["username"]
    except KeyError:
        return {"success": False, "msg": "missing team_username"}, 400
    try:
        email = request.form["email"]
    except KeyError:
        return {"success": False, "msg": "missing email"}, 400
    if not validate_team_username(team_username):
        return {
            "success": False,
            "msg": "invalid team_username: must be between 3 and 100 characters",
        }
    if not validate_email(email):
        return {"success": False, "msg": "invalid email"}, 400
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
                return {
                    "success": False,
                    "msg": "{} already taken.".format(
                        re.match(r"^Key \((.+)\)=", e.diag.message_detail).group(1)
                    ),
                }
            conn.commit()
            return {"success": True, "token": authentication.new_session(str(team_id))}


@blueprint.route("/profile", methods=["GET"])
def profile():
    """Returns profile information

    for now, returns team username, team email, and login url"""
    with connect_pg() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT team_username, team_email from teams where team_id = %s",
                (g.session["team_id"],),
            )
            res = cur.fetchone()
            if res is None:
                cur.execute(
                    "INSERT INTO teams (team_id, team_username, team_email) VALUES (%s, NULL, NULL)",
                    (g.session["team_id"],),
                )
                username = None
                email = None
            else:
                username, email = res
            conn.commit()

    t = LoginToken(g.session["team_id"])
    return {
        "success": True,
        "username": username,
        "email": email,
        "login_url": t.get_login_url(),
    }


@blueprint.route("/profile", methods=["PATCH"])
def update_profile():
    """Updates information in the profile (email, team name)"""
    with connect_pg() as conn:
        with conn.cursor() as cur:
            if "username" in request.form:
                if validate_team_username(request.form["username"]):
                    cur.execute(
                        "UPDATE teams SET team_username = %s WHERE team_id = %s",
                        (request.form["username"], g.session["team_id"]),
                    )
                else:
                    conn.rollback()
                    return {"success": False, "msg": "Invalid new username"}, 400
            if "email" in request.form:
                if validate_email(request.form["email"]):
                    cur.execute(
                        "UPDATE teams SET team_email = %s WHERE team_id = %s",
                        (request.form["email"], g.session["team_id"]),
                    )
                else:
                    conn.rollback()
                    return {"success": False, "msg": "Invalid new username"}, 400
            conn.commit()
    return {"success": True, "msg": "Successfully updated profile"}


@blueprint.route("/login", methods=["POST"])
def login():
    """Allows users to login using login urls"""
    try:
        token = request.form["login_token"]
    except KeyError:
        return {"success": False, "msg": "Missing login token"}, 401
    try:
        account = LoginToken.decode(token)
    except ValueError:
        return {"success": False, "msg": "Invalid token"}, 401
    return {
        "success": True,
        "token": authentication.new_session(account.team_id),
        "msg": "Successfully logged in",
    }


if config.dev:

    @blueprint.route("/dev_login", methods=["POST"])
    def dev_login():
        """Force login as specific team_id

        For development only; passing in non-uuids may cause unintended behavior.
        Use /register instead for all normal usage.
        """

        try:
            team_id = request.form["team_id"]
        except KeyError:
            return {"status": "missing_team_id", "msg": "missing team ID"}, 400
        return {"status": "ok", "token": authentication.new_session(team_id)}
