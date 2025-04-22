# app/routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for # Added flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Recipe, User, CookingLog, db # Import CookingLog and db
from datetime import date, datetime, timedelta # Import date/time

main = Blueprint('main', __name__)

# --- HTML Page Routes ---
@main.route('/')
def index():
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

# --- NEW: Route to view a specific recipe ---
@main.route('/view_recipe/<int:recipe_id>')
@login_required
def view_recipe(recipe_id):
    """API endpoint to get a specific recipe by ID."""
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        # Verify that the recipe belongs to the current user
        if recipe.user_id != current_user.id:
            flash('You can only view your own recipes.', 'warning')
            return redirect(url_for('main.home'))
        return render_template('view_recipe.html', recipe=recipe)
    except Exception as e:
        print(f"Error fetching recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to fetch recipe"}), 500

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

@main.route('/api/recipes', methods=['POST'])
@login_required
def add_recipe():
    """API endpoint to add a new recipe (associated with current user)."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    # Match fields from Recipe model
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions']
    # 'date' is set automatically by frontend, 'image' is optional
    if not all(field in data and data[field] is not None for field in required_fields):
        # Allow empty ingredients list/string? Handled by setter. Check others.
        if not data.get('name') or not data.get('category') or data.get('time') is None or not data.get('instructions'):
            return jsonify({"error": "Missing required fields (name, category, time, instructions)"}), 400

    try:
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
    except Exception as e:
        db.session.rollback()
        print(f"Error adding recipe (database issue): {e}")
        return jsonify({"error": "Failed to add recipe"}), 500

@main.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
@login_required
def delete_recipe_api(recipe_id):
    """API endpoint to delete a specific recipe by ID."""
    try:
        recipe = Recipe.query.get_or_404(recipe_id)

        # Authorization Check
        if recipe.user_id != current_user.id:
             return jsonify({"error": "Unauthorized to delete this recipe"}), 403

        # Check if there are cooking logs associated with this recipe
        if recipe.cooking_logs:
             flash("Cannot delete recipe because it has cooking logs associated with it. Delete the logs first.", "warning")
             # You might want to return a specific status code or error message
             return jsonify({"error": "Cannot delete recipe with existing cooking logs"}), 409 # 409 Conflict

        db.session.delete(recipe)
        db.session.commit()
        return jsonify({"message": "Recipe deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to delete recipe"}), 500


# --- Placeholders (Update or Remove as needed) ---
# Remove the simple placeholder /mykitchen, /dashboard, /share
# routes as those features are integrated differently now (tabs in home.html, new log routes)
# OR create proper server-rendered pages for them if desired later.