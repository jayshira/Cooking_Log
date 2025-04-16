# config.py
import os

# Determine the absolute path of the directory containing config.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Construct the database path relative to the project root (BASE_DIR)
DATABASE_PATH = os.path.join(BASE_DIR, 'recipes.db')

class Config:
    """Base configuration class."""
    # Secret key is needed for sessions, CSRF protection, etc.
    # Use an environment variable in production, provide a default for development
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable modification tracking overhead

    # Add other configurations here if needed