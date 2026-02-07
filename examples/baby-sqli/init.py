import secrets
import sqlite3

con = sqlite3.connect("./login.db")
cur = con.cursor()

cur.execute("CREATE TABLE users(username text, password text)")
cur.execute(
    "INSERT INTO users(username, password) VALUES (?, ?)",
    ("admin", secrets.token_bytes(16).hex()),
)

con.commit()
con.close()
