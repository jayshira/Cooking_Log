# run.py
from app import create_app # Import the factory function from the app package
from config import DevelopmentConfig
# Create the Flask app instance using the factory
app = create_app(DevelopmentConfig)

# Entry point for running the development server
if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', True), host='0.0.0.0')