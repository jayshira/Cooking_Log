# app/routes.py
<<<<<<< Updated upstream
from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for
from flask_login import login_required, current_user # Import Flask-Login utilities
from .models import Recipe, User # Import database models
from . import db                # Import db instance from the app package
=======
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for # Added flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Recipe, User, CookingLog, db # Import CookingLog and db
from datetime import date, datetime, timedelta # Import date/time
>>>>>>> Stashed changes

# Create a Blueprint named 'main' for core application routes and API endpoints.
main = Blueprint('main', __name__)


# --- HTML Page Routes ---

@main.route('/')
def index():
<<<<<<< Updated upstream
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
=======
    # If user is logged in, maybe redirect to home? Optional.
    # if current_user.is_authenticated:
    #    return redirect(url_for('main.home'))
    return render_template('index.html', title='Welcome')

@main.route('/home')
@login_required # Keep protected
def home():
    # Fetch recent logs and streak for the logged-in user
    recent_logs = []
    streak = 0
    if current_user.is_authenticated:
        recent_logs = CookingLog.query.filter_by(user_id=current_user.id)\
                                    .order_by(CookingLog.date_cooked.desc(), CookingLog.created_at.desc())\
                                    .limit(5).all()
        streak = current_user.current_streak

    # Pass logs and streak to the template
    return render_template('home.html', current_user=current_user, recent_logs=recent_logs, current_streak=streak)

# --- NEW: Route to start the cooking session page ---
@main.route('/start_cooking/<int:recipe_id>')
@login_required
def start_cooking_session(recipe_id):
    """Displays the page for an active cooking session."""
    recipe = Recipe.query.get_or_404(recipe_id)

    # Optional but recommended: Check if the user owns the recipe or has permission
    # If you implement sharing later, this logic might change
    if recipe.user_id != current_user.id:
         flash('You can only start cooking sessions for your own recipes.', 'warning')
         return redirect(url_for('main.home'))

    # Pass today's date for the form default
    today_iso = date.today().isoformat()
    return render_template('cooking_session.html', recipe=recipe, today_iso=today_iso)

# --- NEW: Route to handle the submission of the cooking log ---
@main.route('/log_cooking/<int:recipe_id>', methods=['POST'])
@login_required
def log_cooking_session(recipe_id):
    """Handles the submission of the cooking log form."""
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
         flash('You cannot log a session for a recipe you do not own.', 'error')
         return redirect(url_for('main.home'))

    try:
        # Get data from form
        duration_str = request.form.get('duration_seconds')
        rating_str = request.form.get('rating')
        notes = request.form.get('notes')
        date_cooked_str = request.form.get('date_cooked', date.today().isoformat())

        # Validate and convert data
        duration_seconds = int(duration_str) if duration_str and duration_str.isdigit() else None # Allow Null duration
        rating = int(rating_str) if rating_str and rating_str.isdigit() else None # Allow Null rating
        date_cooked = date.fromisoformat(date_cooked_str)

        # --- Cooking Streak Logic ---
        user = User.query.get(current_user.id) # Get fresh user object to update
        today = date.today() # The actual current date

        # Determine if streak should change based on the *date_cooked* from the form
        last_known_cook_date = user.last_cooked_date

        if last_known_cook_date:
            days_difference = (date_cooked - last_known_cook_date).days
            if days_difference == 1:
                # Cooked on the day immediately following the last logged cook day
                user.current_streak += 1
            elif days_difference > 1:
                 # Gap in cooking, reset streak to 1 (assumes this log is the start of a new streak)
                 user.current_streak = 1
            elif days_difference == 0:
                 # Cooked again on the same day, streak doesn't change
                 pass
            else: # days_difference < 0
                 # Logged a past date, doesn't increase streak, might break an existing one if logged between streak days (complex case - ignore for now)
                 # For simplicity, we don't retroactively break streaks here.
                 pass
        else:
             # First time cooking ever logged for this user
             user.current_streak = 1

        # Update last cooked date *if* this log's date is the latest recorded cook date for the user
        if user.last_cooked_date is None or date_cooked > user.last_cooked_date:
             user.last_cooked_date = date_cooked
        # --- End Streak Logic ---

        # Create the log entry
        new_log = CookingLog(
            user_id=current_user.id,
            recipe_id=recipe.id,
            date_cooked=date_cooked,
            duration_seconds=duration_seconds,
            rating=rating,
            notes=notes
        )

        db.session.add(new_log)
        # Need to add the user object to the session if its attributes were changed
        db.session.add(user)
        db.session.commit() # Commit log and user streak updates together

        flash(f'Successfully logged your cooking session for "{recipe.name}"!', 'success')
        return redirect(url_for('main.home')) # Redirect back to home page

    except Exception as e:
        db.session.rollback() # Rollback in case of error
        print(f"ERROR logging cooking session: {e}") # Log for debugging
        flash(f'Error logging cooking session. Please check your input.', 'danger')
        # Redirect back to the cooking session page to allow correction
        return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))


# --- API Routes (Keep existing ones) ---
@main.route('/api/recipes', methods=['GET'])
@login_required # Make API GET also require login if only showing user's recipes
def get_recipes():
    """API endpoint to get recipes for the logged-in user."""
    try:
        # Filter recipes by the current logged-in user
        recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.id.desc()).all()
        return jsonify([recipe.to_dict() for recipe in recipes]), 200
    except Exception as e:
        print(f"Error fetching user recipes: {e}")
        return jsonify({"error": "Failed to fetch recipes"}), 500
>>>>>>> Stashed changes


# POST /api/recipes - Adds a new recipe for the logged-in user
@main.route('/api/recipes', methods=['POST'])
<<<<<<< Updated upstream
@login_required # Require login to add recipes
=======
@login_required
>>>>>>> Stashed changes
def add_recipe():
    """API endpoint to add a new recipe, associated with the current user."""
    # Ensure the request content type is JSON.
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400 # 400 Bad Request

<<<<<<< Updated upstream
    data = request.get_json() # Get JSON data from the request body
=======
    data = request.get_json()
    # Match fields from Recipe model
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions']
    # 'date' is set automatically by frontend, 'image' is optional
    if not all(field in data and data[field] is not None for field in required_fields):
        # Allow empty ingredients list/string? Handled by setter. Check others.
        if not data.get('name') or not data.get('category') or data.get('time') is None or not data.get('instructions'):
            return jsonify({"error": "Missing required fields (name, category, time, instructions)"}), 400
>>>>>>> Stashed changes

    # --- Server-Side Validation ---
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions']
    # Check if data exists and all required fields are present and not empty/None.
    if not data or not all(field in data and data[field] not in [None, ''] for field in required_fields):
        missing = [field for field in required_fields if not data or field not in data or data[field] in [None, '']]
        return jsonify({"error": f"Missing or empty required fields: {', '.join(missing)}"}), 400

    # Validate data types and values more specifically.
    try:
<<<<<<< Updated upstream
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
=======
        # Use the ingredients setter which handles list or comma-separated string
        new_recipe = Recipe(
            name=data['name'],
            category=data['category'],
            time=int(data['time']), # Already validated as number in JS
            ingredients=data['ingredients'], # Use the setter
            instructions=data['instructions'],
            date=data.get('date', datetime.utcnow().isoformat()), # Use provided date or default
            image=data.get('image'),
            user_id=current_user.id # Associate with the logged-in user
        )
        db.session.add(new_recipe)
        db.session.commit()
        # Return the full dict including the generated ID and author
        return jsonify(new_recipe.to_dict()), 201
    except (ValueError, TypeError) as e:
        db.session.rollback()
        print(f"Error adding recipe (data issue): {e}")
        return jsonify({"error": "Invalid data format (e.g., time must be a number)"}), 400
>>>>>>> Stashed changes
    except Exception as e:
        # Rollback the transaction in case of a database error.
        db.session.rollback()
        print(f"Error adding recipe for user {current_user.id}: {e}")
        return jsonify({"error": "Failed to add recipe due to a server error"}), 500


# DELETE /api/recipes/<recipe_id> - Deletes a specific recipe
@main.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
<<<<<<< Updated upstream
@login_required # Require login to delete recipes
=======
@login_required
>>>>>>> Stashed changes
def delete_recipe_api(recipe_id):
    """API endpoint to delete a specific recipe by its ID."""
    try:
        # Fetch the recipe by ID. If not found, Flask-SQLAlchemy's get_or_404
        # will automatically raise a 404 Not Found error.
        recipe = Recipe.query.get_or_404(recipe_id)

<<<<<<< Updated upstream
        # --- Authorization Check ---
        # Verify that the recipe belongs to the currently logged-in user.
        if recipe.user_id != current_user.id:
             # If the user doesn't own the recipe, raise a 403 Forbidden error.
             # abort() is a Flask function to immediately stop request handling with an error code.
             abort(403, description="You are not authorized to delete this recipe.")
             # Alternative: return jsonify({"error": "Unauthorized"}), 403
=======
        # Authorization Check
        if recipe.user_id != current_user.id:
             return jsonify({"error": "Unauthorized to delete this recipe"}), 403

        # Check if there are cooking logs associated with this recipe
        if recipe.cooking_logs:
             flash("Cannot delete recipe because it has cooking logs associated with it. Delete the logs first.", "warning")
             # You might want to return a specific status code or error message
             return jsonify({"error": "Cannot delete recipe with existing cooking logs"}), 409 # 409 Conflict
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream

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
=======

# --- Placeholders (Update or Remove as needed) ---
# Remove the simple placeholder /mykitchen, /dashboard, /share
# routes as those features are integrated differently now (tabs in home.html, new log routes)
# OR create proper server-rendered pages for them if desired later.
>>>>>>> Stashed changes
