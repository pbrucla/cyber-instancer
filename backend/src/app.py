from flask import Flask
from flask import send_file
import redis
import backend
from config import config, rclient as r

app = Flask(__name__, static_url_path="", static_folder="static")


@app.route("/")
def hello():
    return send_file("static/index.html")


@app.route("/api/me")
def hello_world():
    count = r.incr("count")
    return f"<p>Hello, World! {count}</p>"


if __name__ == "__main__":
    app.run(debug=True)
