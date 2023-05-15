from flask import Flask
from flask import send_from_directory
import os
import redis
import backend
from config import config, rclient as r

app = Flask(__name__, static_folder="static")


@app.route("/api/me")
def hello_world():
    count = r.incr("count")
    return f"<p>Hello, World! {count}</p>"


# Serve react app
@app.route("/")
@app.route("/profile")
@app.route("/challs")
@app.route("/chall/<string:chall_id>")
@app.route("/login")
@app.route("/register")
def react(chall_id=""):
    return send_from_directory(app.static_folder, "index.html")


# Serve static files
@app.route("/<path:path>")
def serve(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(debug=True)
