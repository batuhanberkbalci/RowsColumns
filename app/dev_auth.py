"""DEV-ONLY login so the locations feature can be run and tested on its own.

Replace this module with Batuhan's authentication (FR-01 / NFR-01).
The locations feature only relies on `current_user` exposing:
    .organization_id, .role, .membership_status, .is_active, .full_name
and on the login manager's `login_view` pointing at the real login page.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from .db import get_db
from .extensions import login_manager

bp = Blueprint("auth", __name__)

USER_COLUMNS = (
    "user_id, organization_id, email, full_name, password_hash, "
    "role, membership_status, is_active"
)


class User(UserMixin):
    def __init__(self, row):
        self.id = row["user_id"]
        self.organization_id = row["organization_id"]
        self.email = row["email"]
        self.full_name = row["full_name"]
        self.role = row["role"]
        self.membership_status = row["membership_status"]
        self._is_active = row["is_active"]

    @property
    def is_active(self):
        return self._is_active


@login_manager.user_loader
def load_user(user_id):
    with get_db().cursor() as cur:
        cur.execute(f"SELECT {USER_COLUMNS} FROM app_user WHERE user_id = %s", (int(user_id),))
        row = cur.fetchone()
    return User(row) if row else None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db().cursor() as cur:
            cur.execute(
                f"SELECT {USER_COLUMNS} FROM app_user WHERE lower(email) = %s", (email,)
            )
            row = cur.fetchone()

        if not row or not row["is_active"] or not check_password_hash(row["password_hash"], password):
            flash("Invalid email or password.", "danger")
        elif row["membership_status"] != "approved":
            flash("Your membership has not been approved yet.", "warning")
        else:
            login_user(User(row))
            return redirect(url_for("locations.index"))
    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
