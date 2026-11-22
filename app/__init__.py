from flask import Flask, redirect, render_template, url_for

from config import Config

from .db import close_db
from .extensions import csrf, login_manager


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    csrf.init_app(app)
    login_manager.init_app(app)
    app.teardown_appcontext(close_db)

    from . import dev_auth  # replace with the team's real auth blueprint
    from .locations import bp as locations_bp

    app.register_blueprint(dev_auth.bp)
    app.register_blueprint(locations_bp)

    @app.get("/")
    def home():
        return redirect(url_for("locations.index"))

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    return app
