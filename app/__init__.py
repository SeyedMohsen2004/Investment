from flask import Flask
from flask_jwt_extended import JWTManager # type: ignore
from app.config import config
from app.models import db
from app.auth import auth
from app.investment import investment
from app.admin import admin 

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(auth, url_prefix='/api/v1/auth')
    app.register_blueprint(investment, url_prefix='/api/v1/investments')  
    app.register_blueprint(admin, url_prefix='/api/v1/admin') 

    return app
