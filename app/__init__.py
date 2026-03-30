import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY")

    from app.database import init_db
    with app.app_context():
        init_db()

    from app.routes import api
    app.register_blueprint(api)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def frontend(path):
        return render_template("index.html")

    return app
