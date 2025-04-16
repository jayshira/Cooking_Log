# run.py
from app import create_app # Import the factory function from the app package

# Create the Flask app instance using the factory
app = create_app()

# Entry point for running the development server
if __name__ == '__main__':
    # debug=True enables auto-reloading and interactive debugger
    # Use host='0.0.0.0' to make it accessible on your network
    app.run(debug=True, host='0.0.0.0')