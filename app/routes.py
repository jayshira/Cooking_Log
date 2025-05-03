# app/routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Recipe, User, CookingLog, db # Import models and db
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo # Use zoneinfo for Python 3.9+

# If using Python < 3.9, install pytz (pip install pytz) and use:
# import pytz
# PERTH_TZ = pytz.timezone('Australia/Perth')

# Define Perth Timezone
PERTH_TZ = ZoneInfo("Australia/Perth")

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
        # Ensure current_user is fetched with updated data if necessary,
        # though Flask-Login usually handles this on request.
        # For safety, can re-fetch: user = User.query.get(current_user.id)
        user = User.query.get(current_user.id)
        if user: # Check if user exists
             recent_logs = CookingLog.query.filter_by(user_id=user.id)\
                                         .order_by(CookingLog.date_cooked.desc(), CookingLog.created_at.desc())\
                                         .limit(5).all()
             streak = user.current_streak
        else:
            # Handle case where user might not be found (edge case)
            flash("Error loading user data.", "warning")


    # Pass logs and streak to the template
    return render_template('home.html', current_user=current_user, recent_logs=recent_logs, current_streak=streak)

# --- Route to view a specific recipe page ---
@main.route('/view_recipe/<int:recipe_id>')
@login_required
def view_recipe(recipe_id):
    """Displays the details page for a specific recipe."""
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        # Verify that the recipe belongs to the current user
        if recipe.user_id != current_user.id:
            flash('You can only view your own recipes.', 'warning')
            return redirect(url_for('main.home'))
        # Pass the recipe object to the template
        return render_template('view_recipe.html', recipe=recipe)
    except Exception as e:
        print(f"Error fetching recipe page {recipe_id}: {e}")
        flash('Error displaying recipe details.', 'danger')
        return redirect(url_for('main.home'))

# --- Route to start the cooking session page ---
@main.route('/start_cooking/<int:recipe_id>')
@login_required
def start_cooking_session(recipe_id):
    """Displays the page for an active cooking session."""
    recipe = Recipe.query.get_or_404(recipe_id)

    # Check if the user owns the recipe
    if recipe.user_id != current_user.id:
         flash('You can only start cooking sessions for your own recipes.', 'warning')
         return redirect(url_for('main.home'))

    # Pass today's date for the form default
    today_iso = date.today().isoformat()
    return render_template('cooking_session.html', recipe=recipe, today_iso=today_iso)

# --- Route to handle the submission of the cooking log ---
@main.route('/log_cooking/<int:recipe_id>', methods=['POST'])
@login_required
def log_cooking_session(recipe_id):
    """Handles the submission of the cooking log form."""
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
         flash('You cannot log a session for a recipe you do not own.', 'error')
         return redirect(url_for('main.home'))

    try:
        # Get data from form (using request.form for standard POST)
        duration_str = request.form.get('duration_seconds')
        rating_str = request.form.get('rating')
        notes = request.form.get('notes')
        date_cooked_str = request.form.get('date_cooked') # Get date from form

        # Validate date_cooked
        if not date_cooked_str:
             flash('Date cooked is required.', 'danger')
             return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))
        try:
            date_cooked = date.fromisoformat(date_cooked_str)
        except ValueError:
            flash('Invalid date format provided.', 'danger')
            return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))

        # Validate and convert other data
        duration_seconds = int(duration_str) if duration_str and duration_str.isdigit() else None
        rating = int(rating_str) if rating_str and rating_str.isdigit() and 1 <= int(rating_str) <= 5 else None

        # --- Refined Cooking Streak Logic ---
        user = User.query.get(current_user.id) # Get fresh user object

        today_perth = datetime.now(PERTH_TZ).date()
        last_known_cook_date = user.last_cooked_date

        # 1. Check if streak is broken based on CURRENT DATE
        if last_known_cook_date:
            days_since_last_cook = (today_perth - last_known_cook_date).days
            if days_since_last_cook > 1:
                user.current_streak = 0 # Reset streak

        # 2. Process impact of the NEWLY LOGGED date_cooked
        if last_known_cook_date:
            days_difference_from_log = (date_cooked - last_known_cook_date).days
            if days_difference_from_log == 1:
                user.current_streak += 1 # Increment
            elif days_difference_from_log > 1:
                 user.current_streak = 1 # Start new streak
            # else: days_difference_from_log <= 0 -> No change based on this log
        else:
             user.current_streak = 1 # First log ever

        # 3. Update last_cooked_date if this log is the latest known
        if user.last_cooked_date is None or date_cooked >= user.last_cooked_date: # Use >= to handle multiple logs on same day
             user.last_cooked_date = date_cooked
        # --- End Refined Streak Logic ---

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
        db.session.add(user) # Add user to session since streak/last_date might change
        db.session.commit()

        flash(f'Successfully logged your cooking session for "{recipe.name}"!', 'success')
        return redirect(url_for('main.home'))

    except Exception as e:
        db.session.rollback()
        print(f"ERROR logging cooking session: {e}")
        # import traceback # Uncomment for detailed debugging
        # traceback.print_exc() # Uncomment for detailed debugging
        flash(f'An error occurred while logging the cooking session.', 'danger')
        return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))


# --- API Routes ---

# GET all recipes for the logged-in user
@main.route('/api/recipes', methods=['GET'])
@login_required
def get_recipes():
    """API endpoint to get recipes for the logged-in user."""
    try:
        recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.id.desc()).all()
        return jsonify([recipe.to_dict() for recipe in recipes]), 200
    except Exception as e:
        print(f"Error fetching user recipes: {e}")
        return jsonify({"error": "Failed to fetch recipes"}), 500

# POST a new recipe
@main.route('/api/recipes', methods=['POST'])
@login_required
def add_recipe():
    """API endpoint to add a new recipe (associated with current user)."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    # Basic validation for required fields
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions']
    if not all(field in data and data[field] is not None for field in required_fields):
         # More specific check for potentially empty but required fields
         if not data.get('name') or not data.get('category') or data.get('time') is None or not data.get('instructions') or data.get('ingredients') is None:
              return jsonify({"error": "Missing required fields (name, category, time, ingredients, instructions)"}), 400

    try:
        # Further validation
        time_val = int(data['time'])
        if time_val <= 0:
             return jsonify({"error": "Time must be a positive number"}), 400

        new_recipe = Recipe(
            name=data['name'],
            category=data['category'],
            time=time_val,
            ingredients=data['ingredients'], # Uses the setter for list/string handling
            instructions=data['instructions'],
            date=data.get('date', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')), # Store creation timestamp maybe? Or just date. Using ISO format default from JS is fine too.
            image=data.get('image'), # Optional image
            user_id=current_user.id # Associate with the logged-in user
        )
        db.session.add(new_recipe)
        db.session.commit()
        return jsonify(new_recipe.to_dict()), 201 # 201 Created
    except (ValueError, TypeError) as e:
        db.session.rollback()
        print(f"Error adding recipe (data issue): {e}")
        return jsonify({"error": "Invalid data format (e.g., time must be a number)"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error adding recipe (database issue): {e}")
        # import traceback; traceback.print_exc() # For debug
        return jsonify({"error": "Failed to add recipe"}), 500

# DELETE a specific recipe
@main.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
@login_required
def delete_recipe_api(recipe_id):
    """API endpoint to delete a specific recipe by ID."""
    try:
        recipe = Recipe.query.get_or_404(recipe_id)

        # Authorization Check
        if recipe.user_id != current_user.id:
             return jsonify({"error": "Unauthorized to delete this recipe"}), 403

        # Check for associated cooking logs
        if recipe.cooking_logs:
             # Changed flash to be part of the JSON response for API consistency
             # flash("Cannot delete recipe because it has cooking logs associated with it.", "warning")
             return jsonify({"error": "Cannot delete recipe with existing cooking logs. Please delete logs first."}), 409 # 409 Conflict

        db.session.delete(recipe)
        db.session.commit()
        return jsonify({"message": "Recipe deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to delete recipe"}), 500

# PUT (update) a specific recipe
@main.route('/api/recipes/<int:recipe_id>', methods=['PUT'])
@login_required
def update_recipe(recipe_id):
    """API endpoint to update an existing recipe."""
    recipe = Recipe.query.get_or_404(recipe_id)

    # Authorization Check
    if recipe.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to edit this recipe"}), 403 # Corrected this line

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Update fields only if they are present in the payload
        updated = False # Flag to check if anything actually changed
        if 'name' in data and data['name'] and recipe.name != data['name']:
            recipe.name = data['name']
            updated = True
        if 'category' in data and data['category'] and recipe.category != data['category']:
            recipe.category = data['category']
            updated = True
        if 'time' in data:
            try:
                time_val = int(data['time'])
                if time_val > 0 and recipe.time != time_val:
                    recipe.time = time_val
                    updated = True
                elif time_val <=0:
                     print(f"Ignoring invalid time value: {time_val}") # Log attempt to set invalid time
            except (ValueError, TypeError):
                 print(f"Ignoring non-integer time value: {data.get('time')}")
        if 'ingredients' in data: # Use setter, compare json representation? Simpler to just set if provided.
             # Check if ingredients actually changed might be complex, allow update if key exists
             recipe.ingredients = data['ingredients'] # Use the setter
             updated = True # Assume changed if key is present
        if 'instructions' in data and data['instructions'] and recipe.instructions != data['instructions']:
            recipe.instructions = data['instructions']
            updated = True

        # --- CORRECTED IMAGE UPDATE LOGIC ---
        # Only update the image if the 'image' key is present in the payload.
        # This relies on the frontend *not* sending the key if no new image was selected.
        if 'image' in data:
            # You might want to compare if data['image'] is different from recipe.image
            # before setting updated = True, but setting it is generally safe.
            recipe.image = data['image'] # Update with new base64 data or potentially null/""
            updated = True
        # --- END IMAGE UPDATE LOGIC ---

        if updated:
            db.session.commit()
            return jsonify(recipe.to_dict()), 200
        else:
             # Nothing was actually updated
             return jsonify(recipe.to_dict()), 200 # Or maybe 304 Not Modified, but 200 is fine

    except Exception as e:
        db.session.rollback()
        print(f"ERROR updating recipe {recipe_id}: {e}")
        # import traceback; traceback.print_exc() # For debug
        return jsonify({"error": "Failed to update recipe"}), 500


# --- End of File ---