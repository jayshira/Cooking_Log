# app/routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Recipe, User, CookingLog, SharedRecipe, db
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
@main.route('/index')
def index():
    return render_template('index.html')  


@main.route('/home')
@login_required
def home():
    user_id = current_user.id
    # Fetch user fresh from DB to ensure data is up-to-date
    user = db.session.get(User, user_id) 

    recent_logs = []
    streak_display_value = 0 # Default to 0

    if user:
        recent_logs = CookingLog.query.filter_by(user_id=user_id)\
                                    .options(db.joinedload(CookingLog.recipe_logged))\
                                    .order_by(CookingLog.date_cooked.desc(), CookingLog.created_at.desc())\
                                    .limit(5).all()
        
        today_perth = datetime.now(PERTH_TZ).date()
        if user.last_cooked_date:
            days_since_last_cook = (today_perth - user.last_cooked_date).days
            if days_since_last_cook <= 1: 
                streak_display_value = user.current_streak if user.current_streak is not None else 0
            else: 
                streak_display_value = 0
        else: 
            streak_display_value = 0
            
    else:
        flash("Error loading user data.", "warning")

    stats = calculate_user_stats(user_id)

    return render_template('home.html', 
                         recent_logs=recent_logs, 
                         streak=streak_display_value, 
                         log_stats=stats)

# --- Route to view a specific recipe page ---
@main.route('/view_recipe/<int:recipe_id>')
@login_required
def view_recipe(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        
        is_owner = (recipe.user_id == current_user.id)
        
        current_recipe_whitelist = recipe.whitelist if isinstance(recipe.whitelist, list) else []
        is_whitelisted = (current_user.id in current_recipe_whitelist)

        if not is_owner and not is_whitelisted:
            flash('You do not have permission to view this recipe.', 'warning')
            return redirect(url_for('main.home'))
            
        return render_template('view_recipe.html', recipe=recipe, is_owner=is_owner)
    except Exception as e:
        print(f"Error fetching recipe page {recipe_id}: {e}")
        flash('Error displaying recipe details.', 'danger')
        return redirect(url_for('main.home'))


# --- Route to start the cooking session page ---
@main.route('/start_cooking/<int:recipe_id>')
@login_required
def start_cooking_session(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
         flash('You can only start cooking sessions for your own recipes.', 'warning')
         return redirect(url_for('main.home'))
    today_iso = date.today().isoformat()
    return render_template('cooking_session.html', recipe=recipe, today_iso=today_iso)

# --- Route to handle the submission of the cooking log ---
@main.route('/log_cooking/<int:recipe_id>', methods=['POST'])
@login_required
def log_cooking_session(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
         flash('You cannot log a session for a recipe you do not own.', 'error')
         return redirect(url_for('main.home'))

    try:
        duration_str = request.form.get('duration_seconds')
        rating_str = request.form.get('rating')
        notes = request.form.get('notes')
        date_cooked_str = request.form.get('date_cooked')

        if not date_cooked_str:
             flash('Date cooked is required.', 'danger')
             return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))
        try:
            date_cooked = date.fromisoformat(date_cooked_str)
        except ValueError:
            flash('Invalid date format provided.', 'danger')
            return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))

        duration_seconds = int(duration_str) if duration_str and duration_str.isdigit() else None
        rating = int(rating_str) if rating_str and rating_str.isdigit() and 1 <= int(rating_str) <= 5 else None

        user = db.session.get(User, current_user.id)
        if user.current_streak is None: 
            user.current_streak = 0

        original_last_cooked_date = user.last_cooked_date
        
        if original_last_cooked_date:
            days_diff = (date_cooked - original_last_cooked_date).days
            if days_diff == 1: 
                user.current_streak += 1
            elif days_diff > 1: 
                user.current_streak = 1
            elif days_diff <=0 and (user.current_streak == 0 or date_cooked < original_last_cooked_date) : 
                all_logs_dates = sorted(list(set([log.date_cooked for log in CookingLog.query.filter_by(user_id=user.id).all()] + [date_cooked])))
                if not all_logs_dates:
                    user.current_streak = 0
                else:
                    current_recalculated_streak = 0
                    if len(all_logs_dates) > 0:
                        current_recalculated_streak = 1 
                        for i in range(1, len(all_logs_dates)):
                            if (all_logs_dates[i] - all_logs_dates[i-1]).days == 1:
                                current_recalculated_streak += 1
                            elif (all_logs_dates[i] - all_logs_dates[i-1]).days > 1: # Gap resets streak
                                current_recalculated_streak = 1 
                            # If dates are same or out of order but not gapped, streak continues from last point
                    user.current_streak = current_recalculated_streak
        else: 
            user.current_streak = 1
        
        if user.last_cooked_date is None or date_cooked >= user.last_cooked_date:
            user.last_cooked_date = date_cooked
        
        today_perth = datetime.now(PERTH_TZ).date()
        if user.last_cooked_date: 
            days_since_user_last_cook = (today_perth - user.last_cooked_date).days
            if days_since_user_last_cook > 1: 
                user.current_streak = 0 
        else: 
            user.current_streak = 0
        
        if user.current_streak < 0:
            user.current_streak = 0

        new_log = CookingLog(
            user_id=current_user.id, recipe_id=recipe.id, date_cooked=date_cooked,
            duration_seconds=duration_seconds, rating=rating, notes=notes
        )
        db.session.add(new_log); db.session.add(user); db.session.commit()
        flash(f'Successfully logged your cooking session for "{recipe.name}"!', 'success')
        return redirect(url_for('main.home'))

    except Exception as e:
        db.session.rollback()
        print(f"ERROR logging cooking session: {e}")
        flash(f'An error occurred while logging the cooking session: {e}', 'danger')
        return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))

# --- Edit Log Route ---
@main.route('/edit_log/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_log(log_id):
    log_entry = CookingLog.query.get_or_404(log_id)

    if log_entry.user_id != current_user.id:
        flash('You are not authorized to edit this log.', 'danger')
        return redirect(url_for('main.view_logs'))

    if request.method == 'POST':
        try:
            date_cooked_str = request.form.get('date_cooked')
            duration_minutes_str = request.form.get('duration_minutes')
            rating_str = request.form.get('rating')
            notes = request.form.get('notes', '').strip()

            if not date_cooked_str:
                flash('Date cooked is required.', 'danger')
                return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
            try:
                new_date_cooked = date.fromisoformat(date_cooked_str)
            except ValueError:
                flash('Invalid date format for Date Cooked.', 'danger')
                return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')

            new_duration_seconds = None
            if duration_minutes_str and duration_minutes_str.strip():
                try:
                    duration_minutes = int(duration_minutes_str)
                    if duration_minutes < 0:
                        flash('Duration cannot be negative.', 'danger')
                        return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
                    new_duration_seconds = duration_minutes * 60
                except ValueError:
                    flash('Invalid duration format. Please enter a number.', 'danger')
                    return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
            
            new_rating = None
            if rating_str and rating_str.strip(): # If a rating is submitted
                try:
                    rating_val = int(rating_str)
                    if 1 <= rating_val <= 5: new_rating = rating_val
                    else:
                        flash('Rating must be between 1 and 5.', 'danger')
                        return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
                except ValueError:
                    flash('Invalid rating format.', 'danger')
                    return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
            # If no rating_str is submitted (e.g., user cleared it), new_rating remains None

            old_date_cooked = log_entry.date_cooked

            log_entry.date_cooked = new_date_cooked
            log_entry.duration_seconds = new_duration_seconds
            log_entry.rating = new_rating
            log_entry.notes = notes if notes else None 

            db.session.commit() # Commit changes to the log entry first

            # --- Streak Recalculation after log edit ---
            user = db.session.get(User, current_user.id)
            if user.current_streak is None: user.current_streak = 0

            # Fetch all unique log dates for the user, sorted
            all_user_log_dates = sorted(list(set(
                [log.date_cooked for log in CookingLog.query.filter_by(user_id=user.id).all()]
            )))

            if not all_user_log_dates:
                user.current_streak = 0
                user.last_cooked_date = None
            else:
                recalculated_streak = 0
                if len(all_user_log_dates) > 0:
                    recalculated_streak = 1 
                    for i in range(1, len(all_user_log_dates)):
                        days_diff_recalc = (all_user_log_dates[i] - all_user_log_dates[i-1]).days
                        if days_diff_recalc == 1:
                            recalculated_streak += 1
                        elif days_diff_recalc > 1: # Gap in cooking
                            recalculated_streak = 1 
                        # If days_diff_recalc <= 0 (e.g. same day logs), streak based on this pair doesn't advance from prior value
                
                user.current_streak = recalculated_streak
                user.last_cooked_date = all_user_log_dates[-1]

                today_perth = datetime.now(PERTH_TZ).date()
                if user.last_cooked_date:
                    days_since_last_actual_cook = (today_perth - user.last_cooked_date).days
                    if days_since_last_actual_cook > 1:
                        user.current_streak = 0
                else:
                    user.current_streak = 0
            
            if user.current_streak < 0: user.current_streak = 0
            db.session.commit() # Commit changes to the user (streak/last_cooked_date)

            flash('Cooking log updated successfully!', 'success')
            return redirect(url_for('main.view_logs'))

        except Exception as e:
            db.session.rollback()
            print(f"Error updating log (ID: {log_id}): {e}")
            # import traceback; traceback.print_exc();
            flash(f'An error occurred while updating the log: {str(e)}', 'danger')
            return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')

    return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')


# --- API Routes ---
@main.route('/api/recipes', methods=['GET'])
@login_required
def get_recipes():
    try:
        recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.id.desc()).all()
        return jsonify([recipe.to_dict() for recipe in recipes]), 200
    except Exception as e:
        print(f"Error fetching user recipes: {e}")
        return jsonify({"error": "Failed to fetch recipes"}), 500

@main.route('/api/recipes', methods=['POST'])
@login_required
def add_recipe():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions']
    if not all(field in data and data[field] is not None for field in required_fields):
         if not data.get('name') or not data.get('category') or data.get('time') is None or not data.get('instructions') or data.get('ingredients') is None:
              return jsonify({"error": "Missing required fields (name, category, time, ingredients, instructions)"}), 400
    try:
        time_val = int(data['time'])
        if time_val <= 0:
             return jsonify({"error": "Time must be a positive number"}), 400
        new_recipe = Recipe(
            name=data['name'], category=data['category'], time=time_val,
            ingredients=data['ingredients'], instructions=data['instructions'],
            date=data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')),
            image=data.get('image'), user_id=current_user.id
        )
        db.session.add(new_recipe)
        db.session.commit()
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
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        if recipe.user_id != current_user.id:
             return jsonify({"error": "Unauthorized to delete this recipe"}), 403
        # Prevent deletion if logs exist (handled by view_recipe.html JS for UI, but good to have backend check)
        # For direct API calls, this is crucial.
        if CookingLog.query.filter_by(recipe_id=recipe.id).first():
            return jsonify({"error": "Cannot delete recipe with existing cooking logs. Please delete logs first or this feature needs to be implemented."}), 409 # 409 Conflict

        db.session.delete(recipe)
        db.session.commit()
        return jsonify({"message": "Recipe deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to delete recipe"}), 500


@main.route('/api/recipes/<int:recipe_id>', methods=['PUT'])
@login_required
def update_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to edit this recipe"}), 403
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        updated = False
        if 'name' in data and data['name'] and recipe.name != data['name']:
            recipe.name = data['name']; updated = True
        if 'category' in data and data['category'] and recipe.category != data['category']:
            recipe.category = data['category']; updated = True
        if 'time' in data:
            try:
                time_val = int(data['time'])
                if time_val > 0 and recipe.time != time_val:
                    recipe.time = time_val; updated = True
                elif time_val <=0: print(f"Ignoring invalid time value: {time_val}")
            except (ValueError, TypeError): print(f"Ignoring non-integer time value: {data.get('time')}")
        if 'ingredients' in data: # Always treat as update if key is present for JSON list
             recipe.ingredients = data['ingredients']; updated = True
        if 'instructions' in data and data['instructions'] and recipe.instructions != data['instructions']:
            recipe.instructions = data['instructions']; updated = True
        if 'image' in data: # Image can be set to null/empty string to remove it
            recipe.image = data['image']; updated = True
        if updated:
            db.session.commit()
        return jsonify(recipe.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        print(f"ERROR updating recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to update recipe"}), 500
    
@main.route('/api/shared_recipes', methods=['POST'])
@login_required
def create_shared_recipe():
    if not request.is_json: return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    required_fields = ['receiver_name', 'recipe_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    try:
        sharer_name = User.query.get(current_user.id).username
        receiver_name = str(data['receiver_name'])
        recipe_id = int(data['recipe_id'])
        user = User.query.filter_by(username=receiver_name).first()
        if not user: return jsonify({"error": "Receiver not found"}), 404
        receiver_id = user.id
        recipe_to_share = Recipe.query.get(recipe_id)
        if not recipe_to_share: return jsonify({"error": "Recipe not found"}), 404
        
        # Authorization: Ensure sharer owns the recipe
        if recipe_to_share.user_id != current_user.id:
            return jsonify({"error": "You can only share your own recipes."}), 403

        existing_shared = SharedRecipe.query.filter_by(receiver_id=receiver_id, recipe_id=recipe_id).first() # Simpler check
        if existing_shared: return jsonify({"error": "Recipe already shared with this user"}), 409
        
        new_shared = SharedRecipe(
            receiver_id=receiver_id,
            recipe_id=recipe_id,
            sharer_name=sharer_name,
            recipe_name=recipe_to_share.name # Store recipe name for convenience
            )
        db.session.add(new_shared); db.session.commit()
    except ValueError: return jsonify({"error": "Invalid ID format"}), 400
    except Exception as e:
        print(f"Error creating shared recipe: {e}"); db.session.rollback()
        return jsonify({"error": "Failed to create shared recipe"}), 500
    return jsonify({"message": f"Recipe {recipe_id} shared with {receiver_name} successfully."}), 201

@main.route('/api/shared_recipes/my', methods=['GET'])
@login_required
def get_my_shared_recipes():
    try:
        user_id = current_user.id
        # Query shared recipes and join with Recipe table to get recipe details like name
        shared_recipes_data = db.session.query(
                SharedRecipe.id,
                SharedRecipe.recipe_id,
                SharedRecipe.sharer_name,
                SharedRecipe.date_shared,
                Recipe.name.label('recipe_name')  # Get recipe name directly
            ).join(Recipe, SharedRecipe.recipe_id == Recipe.id)\
            .filter(SharedRecipe.receiver_id == user_id)\
            .order_by(SharedRecipe.date_shared.desc())\
            .all()

        # Convert to list of dictionaries
        results = [
            {
                "id": sr.id,
                "recipe_id": sr.recipe_id,
                "sharer_name": sr.sharer_name,
                "date_shared": sr.date_shared.isoformat(), # Ensure JSON serializable
                "recipe_name": sr.recipe_name
            } for sr in shared_recipes_data
        ]
        return jsonify(results), 200
    except Exception as e:
        print(f"Error fetching shared recipes: {e}")
        # import traceback; traceback.print_exc();
        return jsonify({"error": "Failed to fetch shared recipes"}), 500


@main.route('/users/search')
@login_required # Good to protect this, even if it only returns usernames
def user_search():
    q = request.args.get('q', '').strip()
    if len(q) < 2: return jsonify([])
    
    # Exclude current user from search results
    raw_matches = (db.session.query(User.username) # Query only username
                   .filter(User.username.ilike(f"%{q}%"))
                   .filter(User.id != current_user.id) # Exclude self
                   .order_by(User.username).limit(5).all()) # Limit results
    
    usernames = [match[0] for match in raw_matches] # raw_matches is list of tuples
    return jsonify(usernames)

@main.route("/recipes/<int:recipe_id>/whitelist", methods=["POST"])
@login_required
def add_to_whitelist(recipe_id):
    data = request.get_json()
    username_to_whitelist = str(data.get("username", "")).strip()
    if not username_to_whitelist: return jsonify({"error": "Username missing"}), 400
    
    user_to_add = User.query.filter(User.username == username_to_whitelist).first()
    if not user_to_add: return jsonify({"error": f"User '{username_to_whitelist}' not found"}), 404
    
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to manage whitelist for this recipe"}), 403
    if user_to_add.id == current_user.id: # Owner doesn't need to be whitelisted
        return jsonify({"message": "Owner already has full access."}), 200 # Or 400 bad request

    current_recipe_whitelist = list(recipe.whitelist) if recipe.whitelist is not None else []
    if user_to_add.id in current_recipe_whitelist:
        return jsonify({"message": f"User '{user_to_add.username}' is already in the whitelist"}), 200 # Or 409 conflict
    
    current_recipe_whitelist.append(user_to_add.id)
    recipe.whitelist = current_recipe_whitelist # Re-assign to trigger SQLAlchemy change detection for JSON
    
    try:
        db.session.commit()
        # Create a SharedRecipe entry for notification purposes
        recipe_name_for_share = recipe.name
        sharer_name_for_share = current_user.username
        existing_shared_notification = SharedRecipe.query.filter_by(
            receiver_id=user_to_add.id, 
            recipe_id=recipe.id
        ).first()

        if not existing_shared_notification:
            new_shared_notification = SharedRecipe(
                receiver_id=user_to_add.id,
                recipe_id=recipe.id,
                sharer_name=sharer_name_for_share, # Current user is sharing
                recipe_name=recipe_name_for_share
            )
            db.session.add(new_shared_notification)
            db.session.commit()
            
        shared_url = url_for('main.view_recipe', recipe_id=recipe.id, _external=True)
        return jsonify({"message": f"Recipe '{recipe.name}' access granted to {user_to_add.username}. Link: {shared_url}"}), 200
    except Exception as e:
        db.session.rollback(); print(f"Error updating whitelist/shared_recipe for recipe {recipe.id}: {e}")
        return jsonify({"error": "Failed to update whitelist due to a server error"}), 500


@main.route("/recipes/clonerecipe", methods=["POST"])
@login_required
def clone_recipe():
    data = request.get_json(); recipe_id_to_clone = data.get("recipe_id")
    if not recipe_id_to_clone: return jsonify({"error": "Recipe ID missing"}), 400
    
    original_recipe = db.session.get(Recipe, recipe_id_to_clone) 
    if not original_recipe: return jsonify({"error": "Original recipe not found"}), 404
    
    # Check if user can view (and thus clone) the recipe
    is_owner = (original_recipe.user_id == current_user.id)
    current_recipe_whitelist = original_recipe.whitelist if isinstance(original_recipe.whitelist, list) else []
    is_whitelisted = (current_user.id in current_recipe_whitelist)

    if not is_owner and not is_whitelisted:
        return jsonify({"error": "Unauthorized to clone this recipe"}), 403
    
    new_recipe = Recipe(
        name=f"{original_recipe.author.username}'s {original_recipe.name} (Clone)",
        category=original_recipe.category, time=original_recipe.time,
        ingredients=original_recipe.ingredients, # Assumes ingredients are correctly stored/retrieved
        instructions=original_recipe.instructions,
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), # New creation date
        image=original_recipe.image, # Copy image data
        user_id=current_user.id, # New owner is the current user
        whitelist=[] # Cloned recipe has its own empty whitelist
    )
    try:
        db.session.add(new_recipe); db.session.commit()
        return jsonify({"message": f"Recipe '{original_recipe.name}' cloned successfully to your kitchen!",
                        "new_recipe_id": new_recipe.id }), 201 
    except Exception as e:
        db.session.rollback(); print(f"Error cloning recipe {original_recipe.id}: {e}")
        return jsonify({"error": "Failed to clone recipe due to a server error"}), 500

@main.route('/logs')
@login_required
def view_logs():
    user_id = current_user.id
    all_logs = CookingLog.query.filter_by(user_id=user_id)\
                              .options(db.joinedload(CookingLog.recipe_logged))\
                              .order_by(CookingLog.date_cooked.desc(), CookingLog.created_at.desc()).all()
    user_recipes = Recipe.query.filter_by(user_id=user_id).order_by(Recipe.name).all()
    return render_template('logs.html', logs=all_logs, recipes=user_recipes, title='My Cooking Logs')

def calculate_user_stats(user_id):
    stats = {
        'total_sessions': 0, 'most_frequent_recipe': {'name': '-', 'count': 0},
        'total_time_logged_seconds': 0, 'total_time_logged_hours': 0.0,
        'average_rating': 0.0, 'top_recipes_data': [], 'monthly_frequency_data': []
    }
    try:
        stats['total_sessions'] = CookingLog.query.filter_by(user_id=user_id).count()
        total_duration = db.session.query(func.sum(CookingLog.duration_seconds))\
                                  .filter(CookingLog.user_id == user_id, CookingLog.duration_seconds.isnot(None)).scalar()
        stats['total_time_logged_seconds'] = int(total_duration) if total_duration else 0
        stats['total_time_logged_hours'] = round(stats['total_time_logged_seconds'] / 3600, 2)
        avg_rating_query = db.session.query(func.avg(CookingLog.rating))\
                              .filter(CookingLog.user_id == user_id, CookingLog.rating.isnot(None)).scalar()
        stats['average_rating'] = float(avg_rating_query) if avg_rating_query is not None else 0.0 # Handle None from avg

        top_recipes = (db.session.query(Recipe.name, func.count(CookingLog.id).label('log_count'))
                       .join(CookingLog, Recipe.id == CookingLog.recipe_id).filter(CookingLog.user_id == user_id)
                       .group_by(Recipe.name).order_by(desc('log_count')).limit(5).all())
        if top_recipes:
            stats['most_frequent_recipe'] = {'name': top_recipes[0][0], 'count': int(top_recipes[0][1])}
            stats['top_recipes_data'] = [{'name': name, 'count': int(count)} for name, count in top_recipes]
        
        today = date.today(); month_counts = {}
        # Initialize last 12 months including current month
        for i in range(12):
            # Correctly calculate year and month for previous months
            month_to_calc = today.month - i
            year_to_calc = today.year
            if month_to_calc <= 0:
                month_to_calc += 12
                year_to_calc -= 1
            month_counts[f"{year_to_calc:04d}-{month_to_calc:02d}"] = 0

        # Get actual counts from database for the relevant period
        # Define the start date for the last 12 full months from the beginning of the current month
        # Or simpler: just query relevant logs and let python sort it out.
        # For this, we need logs from the last 12 months from today, then group.
        
        # Determine the first day of the month 11 months ago
        first_day_of_period = (today.replace(day=1) - timedelta(days=330)).replace(day=1) # Approximation, then snap to 1st

        monthly_logs = (db.session.query(func.strftime('%Y-%m', CookingLog.date_cooked).label('month'),
                                        func.count(CookingLog.id).label('count'))
                        .filter(CookingLog.user_id == user_id, 
                                CookingLog.date_cooked >= first_day_of_period, # Logs from roughly last 12 months
                                CookingLog.date_cooked <= today) # Up to today
                        .group_by('month').order_by('month').all())
        
        for month_db, count in monthly_logs:
            if month_db in month_counts: # Only update if it's one of our target 12 months
                month_counts[month_db] = int(count)
        
        # Sort keys for chart display (YYYY-MM format sorts naturally)
        sorted_months = sorted(month_counts.keys()) 
        stats['monthly_frequency_data'] = [{'month': m, 'count': month_counts[m]} for m in sorted_months]

    except Exception as e: 
        print(f"Error calculating stats for user {user_id}: {e}")
        # import traceback; traceback.print_exc()
    return stats

# --- End of File ---