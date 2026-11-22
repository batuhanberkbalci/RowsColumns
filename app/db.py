"""One psycopg2 connection per request. Raw SQL only, no ORM."""
import psycopg2
import psycopg2.extras
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(
            current_app.config["DATABASE_URL"],
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        # Anything not committed is rolled back when the connection closes.
        db.close()
