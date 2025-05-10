# app/routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Recipe, User, CookingLog, db
from datetime import date, datetime, timedelta, timezone # <--- MAKE SURE timezone IS IMPORTED HERE
from zoneinfo import ZoneInfo 
from sqlalchemy import func, desc

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
@login_required
def home():
    user_id = current_user.id
    user = db.session.get(User, user_id)

    # --- Fetch Recent Logs and Streak (Existing) ---
    recent_logs = []
    streak = 0
    if user:
        recent_logs = CookingLog.query.filter_by(user_id=user_id)\
                                    .options(db.joinedload(CookingLog.recipe_logged))\
                                    .order_by(CookingLog.date_cooked.desc(), CookingLog.created_at.desc())\
                                    .limit(5).all()
        streak = user.current_streak
    else:
        flash("Error loading user data.", "warning")

    # --- Calculate Log-Based Statistics ---
    log_stats = {
        'total_sessions': 0,
        'most_frequent_recipe': ('-', 0), # (name, count)
        'total_time_logged_seconds': 0,
        'average_rating': 0.0,
        'top_recipes_data': [], # For chart 1: [{'name': 'Recipe A', 'count': 5}, ...]
        'monthly_frequency_data': [] # For chart 2: [{'month': 'YYYY-MM', 'count': 3}, ...]
    }

    try:
        # Query all logs for the user
        user_logs = CookingLog.query.filter_by(user_id=user_id).all()
        log_stats['total_sessions'] = len(user_logs)

        if user_logs:
            # Calculate Total Time Logged (sum non-null durations)
            total_duration = db.session.query(func.sum(CookingLog.duration_seconds))\
                                      .filter(CookingLog.user_id == user_id, CookingLog.duration_seconds.isnot(None))\
                                      .scalar()
            log_stats['total_time_logged_seconds'] = total_duration or 0

            # Calculate Average Rating (avg non-null ratings)
            avg_rating = db.session.query(func.avg(CookingLog.rating))\
                                  .filter(CookingLog.user_id == user_id, CookingLog.rating.isnot(None))\
                                  .scalar()
            log_stats['average_rating'] = float(avg_rating or 0.0) # Ensure float

            # Find Most Frequent Recipe & Top 5 Recipes
            top_recipes_query = db.session.query(
                                        Recipe.name,
                                        func.count(CookingLog.id).label('log_count')
                                    ).join(CookingLog, Recipe.id == CookingLog.recipe_id)\
                                    .filter(CookingLog.user_id == user_id)\
                                    .group_by(Recipe.name)\
                                    .order_by(desc('log_count'))\
                                    .limit(5).all() # Get top 5

            if top_recipes_query:
                 log_stats['most_frequent_recipe'] = (top_recipes_query[0][0], top_recipes_query[0][1]) # First result is most frequent
                 log_stats['top_recipes_data'] = [{'name': name, 'count': count} for name, count in top_recipes_query]

            # Calculate Monthly Frequency (last 12 months including current)
            today = date.today()
            frequency_data = {} # Use dict for easy aggregation
            # Go back 11 months + current month = 12 months total range
            start_date = today - timedelta(days=365) # Approximate start for query efficiency

            monthly_logs_query = db.session.query(
                                        # Extract YYYY-MM format from date_cooked
                                        # Note: SQLite date functions differ from PostgreSQL/MySQL
                                        # Using substr for SQLite: substr(date_cooked, 1, 7)
                                        # Adjust if using a different DB
                                        func.strftime('%Y-%m', CookingLog.date_cooked).label('month'),
                                        func.count(CookingLog.id).label('count')
                                    ).filter(CookingLog.user_id == user_id,
                                             CookingLog.date_cooked >= start_date)\
                                    .group_by('month')\
                                    .order_by('month').all()

            # Initialize frequency counts for the last 12 months
            month_counts = {}
            for i in range(12):
                # Calculate month offset correctly
                year = today.year - (today.month - 1 - i < 0) # Year adjustment if month rolls back
                month = (today.month - 1 - i) % 12 + 1 # Correct month calculation
                month_str = f"{year:04d}-{month:02d}"
                month_counts[month_str] = 0

            # Populate counts from the query
            for month_db, count in monthly_logs_query:
                if month_db in month_counts: # Only include if within the last 12 months range
                     month_counts[month_db] = count

            # Convert to list format for chart, sorted by month
            log_stats['monthly_frequency_data'] = [{'month': m, 'count': c} for m, c in sorted(month_counts.items())]


    except Exception as e:
        print(f"Error calculating log stats: {e}")
        flash("Could not calculate cooking statistics.", "warning")


    # Pass stats data (as JSON string for easy JS parsing) and other data to template
    return render_template('home.html',
                           current_user=current_user,
                           recent_logs=recent_logs,
                           current_streak=streak,
                           log_stats=log_stats) # Pass the dictionary, not the JSON string

# --- Route to view a specific recipe page ---
@main.route('/view_recipe/<int:recipe_id>')
@login_required
def view_recipe(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        
        is_owner = (recipe.user_id == current_user.id)
        
        # Ensure recipe.whitelist is an iterable list for the 'in' check
        current_recipe_whitelist = recipe.whitelist if isinstance(recipe.whitelist, list) else []
        is_whitelisted = (current_user.id in current_recipe_whitelist)

        # User must be the owner OR be whitelisted to view
        if not is_owner and not is_whitelisted:
            flash('You do not have permission to view this recipe.', 'warning')
            return redirect(url_for('main.home'))
            
        # Pass 'is_owner' to the template. If not owner, and they are here, they are whitelisted.
        return render_template('view_recipe.html', recipe=recipe, is_owner=is_owner)
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
        user = db.session.get(User, current_user.id) # Get fresh user object

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
            date=data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')), # Store creation timestamp maybe? Or just date. Using ISO format default from JS is fine too.
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

@main.route('/users/search')
def user_search():
    # Grab the `q` query‑parameter; default to '' if it's missing
    q = request.args.get('q', '').strip()
    
    # If the search term is shorter than 2 characters, return an empty list
    # (avoids hammering the DB for very short queries)
    if len(q) < 2:
        return jsonify([])

    # Build a SQLAlchemy query:
    #  - .filter(...) applies a WHERE clause
    #  - User.name.ilike(...) does a case‑insensitive LIKE '%q%'
    #  - .order_by(User.name) sorts results alphabetically
    #  - .limit(10) caps the number of rows to 10
    # 3. Build a query that SELECTs ONLY the username column:
    #    - db.session.query(User.username) creates a Query for that single column
    #    - .filter(...) applies a case‑insensitive substring match
    #    - .order_by(User.username) sorts alphabetically
    #    - .limit(10) caps results
    #    - .scalars() tells SQLAlchemy “I want the scalar values (strings), not 1‑tuples”
    #    - .all() executes and returns a List[str]
    raw_matches = (
        db.session
          .query(User)
          .with_entities(User.username)
          .filter(User.username.ilike(f"%{q}%"))
          .filter(User.id != current_user.id)
          .order_by(User.username)
          .limit(3)
          .all()
    )

    # 4. Flatten the list of 1‑tuples into a list of strings:
    usernames = [username for (username,) in raw_matches]

    # jsonify(...) serializes the Python list/dict into a JSON response,
    # and sets the proper Content-Type header.
    return jsonify(usernames)

@main.route("/recipes/<int:recipe_id>/whitelist", methods=["POST"])
@login_required
def add_to_whitelist(recipe_id):
    data = request.get_json()
    username_to_whitelist = str(data.get("username", "")).strip()

    if not username_to_whitelist:
        return jsonify({"error": "Username missing"}), 400

    user_to_add = User.query.filter(User.username == username_to_whitelist).first()

    if not user_to_add: # Corrected: Check if user_to_add is None
        return jsonify({"error": f"User '{username_to_whitelist}' not found"}), 404

    recipe = Recipe.query.get_or_404(recipe_id)

    if recipe.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to manage whitelist for this recipe"}), 403
    
    if user_to_add.id == current_user.id:
        return jsonify({"message": "Owner already has full access and cannot be whitelisted."}), 200 # Or 400

    # Initialize recipe.whitelist if it's None or not a list (for older records)
    # The model default=lambda: [] should handle new recipes.
    current_recipe_whitelist = list(recipe.whitelist) if recipe.whitelist is not None else []

    if user_to_add.id in current_recipe_whitelist:
        return jsonify({"message": f"User '{user_to_add.username}' is already in the whitelist"}), 200

    current_recipe_whitelist.append(user_to_add.id) # Add the integer ID
    recipe.whitelist = current_recipe_whitelist # Re-assign to ensure SQLAlchemy detects change for JSON
    
    try:
        db.session.commit()
        shared_url = url_for('main.view_recipe', recipe_id=recipe.id, _external=True)
        return jsonify({
            "message": f"Recipe '{recipe.name}' shared with {user_to_add.username}. Link: {shared_url}"
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating whitelist for recipe {recipe.id}: {e}")
        return jsonify({"error": "Failed to update whitelist due to a server error"}), 500

@main.route("/recipes/clonerecipe", methods=["POST"])
@login_required
def clone_recipe():
    data = request.get_json()
    recipe_id_to_clone = data.get("recipe_id")
    
    if not recipe_id_to_clone:
        return jsonify({"error": "Recipe ID missing"}), 400

    original_recipe = db.session.get(Recipe, recipe_id_to_clone) 
    
    if not original_recipe:
        return jsonify({"error": "Original recipe not found"}), 404
    
    current_recipe_whitelist = original_recipe.whitelist if isinstance(original_recipe.whitelist, list) else []
    if original_recipe.user_id != current_user.id and current_user.id not in current_recipe_whitelist:
        return jsonify({"error": "Unauthorized to clone this recipe"}), 403
    
    new_recipe = Recipe(
        name=f"{original_recipe.author.username}'s {original_recipe.name} (Clone)",
        category=original_recipe.category,
        time=original_recipe.time,
        ingredients=original_recipe.ingredients, 
        instructions=original_recipe.instructions,
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        image=original_recipe.image, 
        user_id=current_user.id,
        whitelist=[] 
    )

    try:
        db.session.add(new_recipe)
        db.session.commit()
        return jsonify({
            "message": f"Recipe '{original_recipe.name}' cloned successfully to your kitchen!",
            "new_recipe_id": new_recipe.id 
        }), 201 
    except Exception as e:
        db.session.rollback()
        print(f"Error cloning recipe {original_recipe.id}: {e}")
        return jsonify({"error": "Failed to clone recipe due to a server error"}), 500

# --- End of File ---