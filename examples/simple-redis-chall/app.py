import redis
from flask import Flask

r = redis.Redis(host="redis")
app = Flask(__name__)


@app.route("/")
def hello():
    return f"<p>Counter: {r.incr('count')}</p>"


if __name__ == "__main__":
    app.run(debug=True)
