from flask import Flask, send_from_directory, request
from instancer import api
import os
import redis
from instancer import backend
from instancer.config import config, rclient as r, connect_pg

app = Flask(__name__, static_folder="static")


@app.route("/api/me")
def hello_world():
    count = r.incr("count")
    return f"<p>Hello, World! {count}</p>"


# Serve APIs
app.register_blueprint(api.blueprint)


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


# Testing
@app.route("/api/test_db")
def test_db():
    if not config.dev:
        return "Disabled due to not in dev mode"
    with connect_pg() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name = %s;",
            [request.args.get("table")],
        )
        return str(cursor.fetchall())


if __name__ == "__main__":
    app.run(debug=True)
