import json
import re
import secrets
import time
import urllib.parse
import uuid
from base64 import b64decode, b64encode

import yaml
from Crypto.Cipher import AES


class LoginToken:
    login_token = None

    def __init__(
        self,
        team_id: str,
        timestamp=None,
        forceUUID=True,
        secret_key=None,
        team_name=None,
        team_email=None,
    ):
        """Initialize a LoginToken given decoded parameters"""

        if secret_key is None and self.login_token is None:
            raise ValueError("Must provide a valid secret key")
        if secret_key is not None and len(b64decode(secret_key)) != 32:
            raise ValueError(
                "Invalid secret login key. Secret login key must be exactly 32 bytes long, base64 encoded"
            )
        if secret_key is not None:
            self.login_token = secret_key
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
    def decode(cls, token):
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

    def get_login_url(self, currentTime=True, url="http://localhost:8080") -> str:
        return "{}/login?token={}".format(
            url, urllib.parse.quote_plus(self.get_token(currentTime=currentTime))
        )

    def get_token(self, currentTime=True):
        login_token = {
            "k": 16,
            "t": (int(time.time()) if currentTime else self.timestamp),
            "d": self.team_id,
        }
        encrypted_token = self.encrypt(json.dumps(login_token, separators=(",", ":")))
        return encrypted_token

    def get_json(self, currentTime=True):
        login_token = {
            "k": 8,
            "t": (int(time.time()) if currentTime else self.timestamp),
            "d": {
                "teamId": self.team_id,
                "name": self.team_name,
                "email": self.team_email,
            },
        }
        return login_token

    @classmethod
    def decrypt(cls, token: str) -> str:
        """
        Given a base64 string, decrypts using the login secret key

        May raise a ValueError, meaning decryption either failed or message integrity check failed
        """
        key = b64decode(cls.login_token)
        data = b64decode(token.encode())
        cipher = AES.new(key, AES.MODE_GCM, data[:12])
        dec = cipher.decrypt_and_verify(data[12:-16], data[-16:])
        return dec.decode("utf-8")

    @classmethod
    def encrypt(cls, json: str) -> str:
        """
        Given any string (usually json string), encrypts using the login secret key
        """
        key = b64decode(cls.login_token)
        dec = str(json).encode()
        nonce = secrets.token_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce)
        enc, mac = cipher.encrypt_and_digest(dec)
        return b64encode(nonce + enc + mac).decode("utf-8")


if __name__ == "__main__":
    custom_token = input(
        "Enter in the login_secret_key, or leave blank to use one in config.yml: "
    )
    if custom_token == "":
        with open("../config.yml", "r") as f:
            try:
                conf = yaml.safe_load(f)
                LoginToken.login_token = conf["login_secret_key"]
                admin_uuid = conf["admin_team_id"]
                instancer_url = conf["url"]
                print("Found valid config")
            except yaml.YAMLError as exc:
                print("Failed to read config file:")
                print(exc)
                exit(1)
    else:
        LoginToken.login_token = custom_token
        admin_uuid = uuid.uuid4()
        instancer_url = "http://localhost:8080"

    while True:
        print(
            """What would you like to do? Type the number:
        1 - Generate a login URL
        2 - Decode a login URL
        3 - Exit
        """
        )
        choice = input()
        if choice == "1":
            input_uuid = input(
                "Enter account UUID (leave blank for random, enter admin to use admin uuid): "
            )
            if input_uuid == "":
                input_uuid = str(uuid.uuid4())
            elif input_uuid == "admin":
                input_uuid = admin_uuid
            else:
                try:
                    uuid.UUID(input_uuid)
                except:
                    print("Invalid Input")
            print("Using uuid {}".format(input_uuid))
            new_token = LoginToken(input_uuid)
            print("Login URL:")
            print(new_token.get_login_url(url=instancer_url))
        elif choice == "2":
            input_encrypted = input("Enter in a login URL or login token: ")
            if "/login?token=" in input_encrypted:
                input_encrypted = input_encrypted.split("login?token=", 2)[1]
            input_encrypted = urllib.parse.unquote(input_encrypted)

            token = LoginToken.decode(input_encrypted)
            print("Token information:")
            print(json.dumps(token.get_json()))
        elif choice == "3":
            exit(0)
        else:
            print("Unexpected input")
