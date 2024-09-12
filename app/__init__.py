from flask import Flask
from flask_jwt_extended import JWTManager
from app.config import config
from app.models import db
from app.auth import auth

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    try:
        db.init_app(app)
    except Exception as e:
        print(f"Error initializing database: {e}")
        return None

    jwt_manager = JWTManager(app)  # Renamed to avoid confusion with import
    jwt_manager.secret_key = app.config['JWT_SECRET_KEY']
    jwt_manager.access_token_expires = app.config['JWT_ACCESS_TOKEN_EXPIRES']

    app.register_blueprint(auth, url_prefix='/api/v1/auth')
    # app.register_blueprint(auth, url_prefix='/api/v1/auth')

    return app
