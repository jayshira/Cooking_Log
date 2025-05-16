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

login_manager.login_view = 'auth.login' # Route name for the login view
login_manager.login_message_category = 'info' # Bootstrap category for the flash message

@login_manager.user_loader
def load_user(user_id):
    from .models import User # Import here to avoid circular dependency
    try:
        # CORRECTED: Use the newer db.session.get()
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        # Handle cases where user_id might not be a valid integer
        return None

def create_app(config_class=Config): # Default to base Config
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    # Initialize Migrate here, passing app and db
    migrate.init_app(app, db) 

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Removed the db.create_all() block as migrations handle this.
    # Ensure models are imported so Flask-Migrate can see them.
    with app.app_context():
        from . import models # noqa: F401 Ensures models are registered with SQLAlchemy

    return app