import os

import requests
import yaml
from token_manager import LoginToken

config_file_path = os.path.join(os.path.dirname(__file__), "../config.yml")

with open(config_file_path, "r") as f:
    try:
        conf = yaml.safe_load(f)
        LoginToken.login_token = conf["login_secret_key"]
        admin_uuid = conf["admin_team_id"]
        url = conf["url"]
        print("Found valid config")
    except yaml.YAMLError as exc:
        print("Failed to read config file:")
        print(exc)
        exit(1)

login_token = LoginToken(admin_uuid)
login_token_url = login_token.get_token()

# print("Login Token: {}".format(login_token_url))
r = requests.post(
    "{}/api/accounts/login".format(url), data={"login_token": login_token_url}
)

print("Login token: {}".format(r.json()["token"]))
