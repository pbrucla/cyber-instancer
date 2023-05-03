from flask import Flask

api = Flask(__name__)

@api.route("/api/me")
def me():
    response_body = {
        "name": "Test"
    }
    return response_body