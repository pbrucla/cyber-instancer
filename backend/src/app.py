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

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    app.run(debug=True)
