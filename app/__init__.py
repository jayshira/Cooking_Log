# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager # Import LoginManager
from flask_bcrypt import Bcrypt      # Import Bcrypt
from config import Config

# Initialize extensions outside the factory function
db = SQLAlchemy()
bcrypt = Bcrypt() # Initialize Bcrypt
login_manager = LoginManager() # Initialize LoginManager

# Configure login view and message category
# 'auth.login' refers to the login route within the 'auth' blueprint we will create
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info' # Bootstrap category for flash messages

# --- User Loader Function ---
# This callback is used to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    # Import the User model here to avoid circular imports at the top level
    from .models import User
    # user_id comes from the session as a string, convert to int for query
    return User.query.get(int(user_id))

# --- Application Factory Function ---
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions with the app instance
    db.init_app(app)
    bcrypt.init_app(app)        # Initialize Bcrypt with app
    login_manager.init_app(app) # Initialize LoginManager with app

    # Import and register Blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Import and register the new auth Blueprint (we'll create auth.py next)
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint) # Register without a prefix for routes like /login

    # Create database tables (consider using Flask-Migrate later)
    with app.app_context():
        from . import models # noqa: F401
        print("Ensuring database tables exist...")
        # This will now create both Recipe and User tables if they don't exist
        db.create_all()
        print("Database tables checked/created.")

    return app