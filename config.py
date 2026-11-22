import os


class Config:
    # Override both in a real deployment via environment variables.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/workspace_booking",
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # CSRF protection for every form that changes data (NFR-02).
    WTF_CSRF_ENABLED = True
