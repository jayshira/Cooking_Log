# app/routes.py
from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for
from flask_login import login_required, current_user # Import Flask-Login utilities
from .models import Recipe, User # Import database models
from . import db                # Import db instance from the app package

# Create a Blueprint named 'main' for core application routes and API endpoints.
main = Blueprint('main', __name__)


# --- HTML Page Routes ---

@main.route('/')
def index():
    """Serves the public landing/welcome page."""
    # If a user is already logged in, redirect them directly to their main dashboard.
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    # Otherwise, show the public index page.
    return render_template('index.html', title='Welcome')


@main.route('/home')
@login_required # This decorator ensures only logged-in users can access this route.
def home():
    """Serves the main application page (dashboard/kitchen) for logged-in users."""
    # Flask-Login makes `current_user` available in templates automatically.
    # We pass 'title' for the page title.
    return render_template('home.html', title='My Kitchen')


# --- API Routes (typically return JSON data) ---

# GET /api/recipes - Fetches recipes for the logged-in user
@main.route('/api/recipes', methods=['GET'])
@login_required # Require login to access user-specific recipes via API
def get_recipes():
    """API endpoint to get all recipes associated with the current logged-in user."""
    try:
        # Query the database for recipes where user_id matches the current user's ID.
        # Order by date added, newest first.
        user_recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.date_added.desc()).all()
        # Convert each Recipe object to a dictionary using the `to_dict()` method.
        # Return the list of dictionaries as a JSON response.
        return jsonify([recipe.to_dict() for recipe in user_recipes]), 200 # 200 OK status
    except Exception as e:
        # Log the error for server-side debugging.
        print(f"Error fetching recipes for user {current_user.id}: {e}")
        # Return a generic error message to the client.
        return jsonify({"error": "Failed to fetch recipes due to a server error"}), 500 # 500 Internal Server Error


# POST /api/recipes - Adds a new recipe for the logged-in user
@main.route('/api/recipes', methods=['POST'])
@login_required # Require login to add recipes
def add_recipe():
    """API endpoint to add a new recipe, associated with the current user."""
    # Ensure the request content type is JSON.
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400 # 400 Bad Request

    data = request.get_json() # Get JSON data from the request body

    # --- Server-Side Validation ---
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions']
    # Check if data exists and all required fields are present and not empty/None.
    if not data or not all(field in data and data[field] not in [None, ''] for field in required_fields):
        missing = [field for field in required_fields if not data or field not in data or data[field] in [None, '']]
        return jsonify({"error": f"Missing or empty required fields: {', '.join(missing)}"}), 400

    # Validate data types and values more specifically.
    try:
        time_val = int(data['time'])
        if time_val <= 0:
            raise ValueError("Time must be a positive integer.")
        # The ingredients setter in the model handles list/string conversion,
        # but we can check the type here if needed.
        if not isinstance(data.get('ingredients'), (list, str)):
             raise ValueError("Ingredients must be a list or a comma-separated string.")
    except (ValueError, TypeError) as e:
         # Return specific validation error message.
         return jsonify({"error": f"Invalid data format: {e}"}), 400

    # --- Create and Save Recipe ---
    try:
        # Create a new Recipe instance.
        new_recipe = Recipe(
            name=data['name'],
            category=data['category'],
            time=time_val,
            # The 'ingredients' property setter in the Recipe model handles conversion
            # from list or comma-separated string to JSON string for storage.
            ingredients=data['ingredients'],
            instructions=data['instructions'],
            # 'date_added' uses the model's default (datetime.utcnow).
            image=data.get('image'), # Optional image (e.g., base64 data URI).
            user_id=current_user.id # Associate the recipe with the logged-in user.
            # Alternatively, use the backref: author=current_user
        )
        db.session.add(new_recipe)
        db.session.commit()
        # Return the newly created recipe's data as JSON.
        return jsonify(new_recipe.to_dict()), 201 # 201 Created status code
    except Exception as e:
        # Rollback the transaction in case of a database error.
        db.session.rollback()
        print(f"Error adding recipe for user {current_user.id}: {e}")
        return jsonify({"error": "Failed to add recipe due to a server error"}), 500


# DELETE /api/recipes/<recipe_id> - Deletes a specific recipe
@main.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
@login_required # Require login to delete recipes
def delete_recipe_api(recipe_id):
    """API endpoint to delete a specific recipe by its ID."""
    try:
        # Fetch the recipe by ID. If not found, Flask-SQLAlchemy's get_or_404
        # will automatically raise a 404 Not Found error.
        recipe = Recipe.query.get_or_404(recipe_id)

        # --- Authorization Check ---
        # Verify that the recipe belongs to the currently logged-in user.
        if recipe.user_id != current_user.id:
             # If the user doesn't own the recipe, raise a 403 Forbidden error.
             # abort() is a Flask function to immediately stop request handling with an error code.
             abort(403, description="You are not authorized to delete this recipe.")
             # Alternative: return jsonify({"error": "Unauthorized"}), 403

        # If authorized, delete the recipe from the database session.
        db.session.delete(recipe)
        # Commit the changes to the database.
        db.session.commit()
        # Return a success message.
        return jsonify({"message": "Recipe deleted successfully"}), 200 # 200 OK
    except Exception as e:
        # Rollback the transaction if any error occurs during deletion.
        db.session.rollback()
        print(f"Error deleting recipe {recipe_id} for user {current_user.id}: {e}")
        # Return a generic server error message.
        return jsonify({"error": "Failed to delete recipe due to a server error"}), 500


# --- Placeholder Routes for Future Features (Protected) ---
# These demonstrate how to create routes that require login and render basic pages.

@main.route('/mykitchen')
@login_required
def my_kitchen():
    """Placeholder route - might be redundant with '/home' or show a different view."""
    # This currently renders a generic placeholder template.
    return render_template('placeholder.html', title='My Kitchen',
                           message=f"Welcome back to your kitchen, {current_user.username}! This page is under construction.")

@main.route('/dashboard')
@login_required
def dashboard():
    """Placeholder route for a user dashboard/insights view."""
    # This would eventually fetch aggregated data and render a template with more stats/charts.
    return render_template('placeholder.html', title='Dashboard',
                           message=f"Your dashboard, {current_user.username}! Statistics and insights will appear here. (Page under construction)")

@main.route('/share')
@login_required
def share():
    """Placeholder route for the sharing management view."""
    # This page would allow users to manage shared recipes, view shared links, etc.
    return render_template('placeholder.html', title='Share Center',
                           message=f"Sharing center for {current_user.username}! Manage your shared recipes here. (Page under construction)")


# --- Note on Placeholder Template ---
# You would need to create a simple `app/templates/placeholder.html` file
# for the above placeholder routes to work. It could look something like this:
#
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <title>{{ title }} - KitchenLog</title>
#     <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
# </head>
# <body>
#     <header>...</header> <!-- Basic header with logo/logout -->
#     <div class="container">
#         <div class="card">
#             <h2>{{ title }}</h2>
#             <p>{{ message }}</p>
#             <p><a href="{{ url_for('main.home') }}">Go back to My Kitchen</a></p>
#         </div>
#     </div>
# </body>
# </html>