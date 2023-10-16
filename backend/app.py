import os

import redis
from flask import Flask, render_template, request
from flask.typing import ResponseReturnValue

from instancer import api, backend
from instancer.config import config, connect_pg
from instancer.config import rclient as r

app = Flask(
    __name__, static_folder="static", static_url_path="/", template_folder="static"
)


# Serve APIs
app.register_blueprint(api.blueprint)


# Serve react app
@app.route("/")
@app.route("/profile")
@app.route("/challs")
@app.route("/chall/<string:chall_id>")
@app.route("/login")
@app.route("/register")
def react(chall_id: str = "") -> ResponseReturnValue:
    return render_template(
        "index.html",
        client_conf={
            "rctf_mode": config.rctf_mode,
            "rctf_url": config.rctf_url,
            "recaptcha_site_key": config.recaptcha_site_key,
        },
    )


# Testing
if config.dev:

    @app.route("/api/test_db")
    def test_db() -> ResponseReturnValue:
        with connect_pg() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name = %s;",
                [request.args.get("table")],
            )
            return str(cursor.fetchall())


if __name__ == "__main__":
    app.run(debug=True)
