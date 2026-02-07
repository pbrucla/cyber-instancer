import os
import sqlite3

from flask import Flask, Response, request

flag = os.environ.get("FLAG", "flag{placeholder_flag}")

app = Flask(__name__)

con = sqlite3.connect("./login.db")
cur = con.cursor()


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return Response(
            "Must include a valid username and password",
            status=400,
            content_type="text/plain",
        )
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    try:
        cur.execute(query)
        msg = (
            "Invalid login"
            if cur.fetchone() is None
            else "Hi user! Here's the flag: " + flag
        )
    except sqlite3.DatabaseError:
        msg = "SQL error"
    return Response(
        f"Executing query {query}\n{msg}", status=400, content_type="text/plain"
    )


@app.route("/")
def hello():
    return """
        <form method="POST" action="/login">
            Username: <input name="username" type="text"><br>
            Password: <input name="password" type="text"><br>
            <input type="submit" value="Login">
        </form>
    """


if __name__ == "__main__":
    app.run(debug=True)
