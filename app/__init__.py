# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db) # <-- Initialize Migrate here, passing app and db

    # Import and register Blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # Database Initialization within application context - REMOVE create_all
    with app.app_context():
        # Import models here AFTER db is initialized and within context
        from . import models # noqa: F401

        # REMOVE OR COMMENT OUT THE FOLLOWING LINES:
        # print("Ensuring database tables exist...")
        # db.create_all() # <-- REMOVE THIS LINE
        # print("Database tables checked/created.")
        pass # Keep the app_context block if needed for other setup later

    return app