from flask import Flask
import redis
import backend
from config import config

app = Flask(__name__)
r = redis.Redis(host=config.redis_host, port=config.redis_port, password=config.redis_password)

@app.route("/")
def hello_world():
    count = r.incr("count")
    return f"<p>Hello, World! {count}</p>"

if __name__ == "__main__":
    app.run(debug=True)
