from functools import wraps

from flask import abort, current_app
from flask_login import current_user


def role_required(*roles):
    """Allow only logged-in, approved, active users with one of `roles`.

    Not logged in  -> redirect to the login page.
    Wrong role     -> 403.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if (
                current_user.role not in roles
                or current_user.membership_status != "approved"
                or not current_user.is_active
            ):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
