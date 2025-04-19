from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager # Import LoginManager
from flask_bcrypt import Bcrypt      # Import Bcrypt
from config import Config          # Import configuration class

# Initialize extensions globally but without an app instance yet
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Configure Flask-Login settings
# 'auth.login' is the endpoint name (blueprint_name.view_function_name) for the login route
login_manager.login_view = 'auth.login'
# The category for flashed messages when redirecting to login
login_manager.login_message_category = 'info' # Use 'info' for Bootstrap alert styling


# --- User Loader Function ---
# This callback is crucial for Flask-Login. It tells Flask-Login how to
# load a user object given the user ID stored in the session cookie.
@login_manager.user_loader
def load_user(user_id):
    """Callback function used by Flask-Login to load a user from the user ID."""
    # Import the User model here to avoid circular imports during initialization
    from .models import User
    try:
        # The user_id stored in the session is usually a string, convert to int for query
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        # Handle cases where user_id is invalid
        return None

# --- Application Factory Function ---
# This pattern allows creating multiple instances of the app with different
# configurations, which is useful for testing and scaling.
def create_app(config_class=Config):
    """Creates and configures the Flask application instance."""

    app = Flask(__name__)
    # Load configuration from the config_class object (e.g., config.Config)
    app.config.from_object(config_class)

    # Initialize Flask extensions with the app instance created by the factory
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Import and register Blueprints within the factory function
    # This avoids circular imports as blueprints might need 'app' or extensions

    # Import the 'main' blueprint (for general routes and API)
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint) # Register without a prefix (routes like /home, /api/recipes)

    # Import the 'auth' blueprint (for authentication routes)
    from .auth import auth as auth_blueprint
    # Register the auth blueprint with a URL prefix
    app.register_blueprint(auth_blueprint, url_prefix='/auth') # Routes like /auth/login, /auth/signup

    # Database Initialization within application context
    with app.app_context():
        # Import models here AFTER db is initialized and within context
        # The noqa comment prevents linters from complaining about unused import,
        # but importing is necessary for SQLAlchemy to detect the models.
        from . import models # noqa: F401

        print("Ensuring database tables exist...")
        # This command creates database tables based on the defined models
        # if they don't already exist. For production or complex changes,
        # using Flask-Migrate is recommended.
        db.create_all()
        print("Database tables checked/created.")

    # Return the configured app instance
    return app