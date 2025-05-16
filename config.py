# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'recipes.db') # For development

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-hard-to-guess-string-indeed'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER_PROFILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads/profile_pics')

    # Add other common configurations here

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{DATABASE_PATH}'

class TestConfig(Config):
    """Testing configuration."""
    TESTING = True  # Enables testing mode in Flask extensions
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory SQLite database
    WTF_CSRF_ENABLED = False # Disable CSRF forms for testing (often simpler for unit tests)
    LOGIN_DISABLED = False # Keep login enabled unless specifically testing unauth access easily
    # You might also want to set a specific SECRET_KEY for tests if needed,
    # but the base one is usually fine.