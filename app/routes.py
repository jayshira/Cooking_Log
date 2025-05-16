# app/routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import Recipe, User, CookingLog, SharedRecipe, db
from datetime import date, datetime, timedelta, timezone # <--- MAKE SURE timezone IS IMPORTED HERE
from zoneinfo import ZoneInfo 
from sqlalchemy import func, desc
import base64 # For image encoding

# If using Python < 3.9, install pytz (pip install pytz) and use:
# import pytz
# PERTH_TZ = pytz.timezone('Australia/Perth')

# Define Perth Timezone
PERTH_TZ = ZoneInfo("Australia/Perth")

main = Blueprint('main', __name__)
# --- Helper function for streak calculation ---
def _recalculate_user_streak_and_last_cooked(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return

    all_user_log_dates = sorted(list(set(
        log.date_cooked for log in CookingLog.query.filter_by(user_id=user.id).all()
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
                elif days_diff_recalc > 1: 
                    recalculated_streak = 1 
        
        user.current_streak = recalculated_streak
        user.last_cooked_date = all_user_log_dates[-1] 

        today_perth = datetime.now(PERTH_TZ).date()
        if user.last_cooked_date:
            days_since_last_actual_cook = (today_perth - user.last_cooked_date).days
            if days_since_last_actual_cook > 1: 
                user.current_streak = 0
        else: 
            user.current_streak = 0
            
    if user.current_streak < 0: 
        user.current_streak = 0
    
    db.session.add(user) # Add user to session for potential commit by caller

# --- HTML Page Routes ---
@main.route('/')
@main.route('/index')
def index():
    return render_template('index.html')  


@main.route('/home')
@login_required
def home():
    user_id = current_user.id
    user = db.session.get(User, user_id) 

    recent_logs = []
    streak_display_value = user.current_streak if user and user.current_streak is not None else 0

    if user:
        recent_logs = CookingLog.query.filter_by(user_id=user_id)\
                                    .options(db.joinedload(CookingLog.recipe_logged))\
                                    .order_by(CookingLog.date_cooked.desc(), CookingLog.created_at.desc())\
                                    .limit(5).all()
        
        # For displaying streak, directly use user.current_streak if last_cooked_date is recent
        # The _recalculate_user_streak_and_last_cooked ensures user.current_streak is 0 if not recent
        today_perth = datetime.now(PERTH_TZ).date()
        if user.last_cooked_date:
            days_since_last_cook = (today_perth - user.last_cooked_date).days
            if days_since_last_cook <= 1: # Cooked today or yesterday
                streak_display_value = user.current_streak if user.current_streak is not None else 0
            else: # Last cook was >1 day ago, streak should be 0 (already handled by recalculate)
                streak_display_value = 0 # Or user.current_streak, which should be 0
        else: # No cooking logs ever
            streak_display_value = 0
            
    else:
        flash("Error loading user data.", "warning")
        streak_display_value = 0 # Safety

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
    # Allow whitelisted users to start cooking shared recipes too, they log it for themselves
    is_owner = (recipe.user_id == current_user.id)
    current_recipe_whitelist = recipe.whitelist if isinstance(recipe.whitelist, list) else []
    is_whitelisted = (current_user.id in current_recipe_whitelist)

    if not is_owner and not is_whitelisted:
         flash('You do not have permission to start a cooking session for this recipe.', 'warning')
         return redirect(url_for('main.view_recipe', recipe_id=recipe.id)) # Or main.home

    today_iso = date.today().isoformat()
    return render_template('cooking_session.html', recipe=recipe, today_iso=today_iso)

# --- Route to handle the submission of the cooking log ---
@main.route('/log_cooking/<int:recipe_id>', methods=['POST'])
@login_required
def log_cooking_session(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id) 
    
    is_owner_of_original = (recipe.user_id == current_user.id)
    current_recipe_whitelist = recipe.whitelist if isinstance(recipe.whitelist, list) else []
    is_whitelisted_for_original = (current_user.id in current_recipe_whitelist)

    if not is_owner_of_original and not is_whitelisted_for_original:
         flash('You cannot log a session for a recipe you do not have access to.', 'error')
         return redirect(url_for('main.home'))

    try:
        duration_str = request.form.get('duration_seconds')
        rating_str = request.form.get('rating')
        notes = request.form.get('notes')
        date_cooked_str = request.form.get('date_cooked')
        
        log_image_url = None
        image_file = request.files.get('log_image')
        if image_file and image_file.filename != '':
            if not image_file.mimetype.startswith('image/'):
                flash('Invalid image file type. Please upload a valid image.', 'danger')
                return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))
            try:
                image_data = image_file.read()
                if len(image_data) > 5 * 1024 * 1024: # Max 5MB
                    flash('Image file is too large (max 5MB).', 'danger')
                    return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))

                base64_image = base64.b64encode(image_data).decode('utf-8')
                log_image_url = f"data:{image_file.mimetype};base64,{base64_image}"
            except Exception as img_e:
                print(f"Error processing log image: {img_e}")
                flash('Could not process the uploaded image.', 'danger')
                # Don't necessarily return, image is optional

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

        new_log = CookingLog(
            user_id=current_user.id, recipe_id=recipe.id, date_cooked=date_cooked,
            duration_seconds=duration_seconds, rating=rating, notes=notes,
            image_url=log_image_url 
        )
        db.session.add(new_log)
        
        # CORRECTED: Call the helper function to update streak and last_cooked_date
        _recalculate_user_streak_and_last_cooked(current_user.id)
        # The user object (current_user or fetched via db.session.get inside helper)
        # will be added to the session by the helper.

        db.session.commit()
        flash(f'Successfully logged your cooking session for "{recipe.name}"!', 'success')
        return redirect(url_for('main.home'))

    except Exception as e:
        db.session.rollback()
        print(f"ERROR logging cooking session: {e}")
        flash(f'An error occurred while logging the cooking session: {str(e)}', 'danger')
        return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))

# --- Edit Log Route ---
@main.route('/edit_log/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_log(log_id):
    log_entry = CookingLog.query.get_or_404(log_id)

    if log_entry.user_id != current_user.id:
        flash('You are not authorized to edit this log.', 'danger')
        return redirect(url_for('main.view_logs')) # Or wherever appropriate

    if request.method == 'POST':
        try:
            # ... (your existing form data processing for log_entry)
            date_cooked_str = request.form.get('date_cooked')
            duration_minutes_str = request.form.get('duration_minutes')
            rating_str = request.form.get('rating')
            notes = request.form.get('notes', '').strip()
            remove_current_image = request.form.get('remove_current_image') == 'yes'
            new_image_file = request.files.get('log_image_edit')

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
            if rating_str and rating_str.strip(): 
                try:
                    rating_val = int(rating_str)
                    if 1 <= rating_val <= 5: new_rating = rating_val
                    else:
                        flash('Rating must be between 1 and 5.', 'danger')
                        return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
                except ValueError:
                    flash('Invalid rating format.', 'danger')
                    return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')

            if new_image_file and new_image_file.filename != '':
                if not new_image_file.mimetype.startswith('image/'):
                    flash('Invalid new image file type. Please upload a valid image.', 'danger')
                    return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
                try:
                    image_data = new_image_file.read()
                    if len(image_data) > 5 * 1024 * 1024: 
                        flash('New image file is too large (max 5MB).', 'danger')
                        return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    log_entry.image_url = f"data:{new_image_file.mimetype};base64,{base64_image}"
                except Exception as img_e:
                    print(f"Error processing new log image during edit: {img_e}")
                    flash('Could not process the new uploaded image.', 'danger')
            elif remove_current_image:
                log_entry.image_url = None
            
            log_entry.date_cooked = new_date_cooked
            log_entry.duration_seconds = new_duration_seconds
            log_entry.rating = new_rating
            log_entry.notes = notes if notes else None
            # No need to db.session.add(log_entry) if it's already tracked by the session
            
            db.session.commit() # Commit changes to the log entry

            # CORRECTED: Call the helper function after committing log changes
            _recalculate_user_streak_and_last_cooked(current_user.id)
            db.session.commit() # Commit changes to the user (streak, last_cooked_date)

            flash('Cooking log updated successfully!', 'success')
            return redirect(url_for('main.view_log_detail', log_id=log_entry.id)) 

        except Exception as e:
            db.session.rollback()
            print(f"Error updating log (ID: {log_id}): {e}")
            flash(f'An error occurred while updating the log: {str(e)}', 'danger')
            # No need to return render_template here if you redirect anyway or if error is severe
            # but if it's a validation error you might want to re-render with the form.
            # For simplicity now, just pass. The render is outside the try/except for POST.

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
        recipe_to_delete = Recipe.query.get_or_404(recipe_id)
        if recipe_to_delete.user_id != current_user.id:
             return jsonify({"error": "Unauthorized to delete this recipe"}), 403

        # Find and delete all cooking logs associated with this recipe.
        logs_to_delete = CookingLog.query.filter_by(recipe_id=recipe_to_delete.id).all()
        for log in logs_to_delete:
            db.session.delete(log)
        
        # Also, remove any SharedRecipe entries related to this recipe_id
        shared_entries_to_delete = SharedRecipe.query.filter_by(recipe_id=recipe_to_delete.id).all()
        for shared_entry in shared_entries_to_delete:
            db.session.delete(shared_entry)

        # After deleting associated items, delete the recipe itself
        db.session.delete(recipe_to_delete)
        db.session.commit()
        
        # Recalculate streak for the current user if any of their logs were deleted
        # This is important if deleting a recipe also deletes logs that affected their streak.
        # If logs_to_delete contained any logs by current_user:
        if any(log.user_id == current_user.id for log in logs_to_delete):
            _recalculate_user_streak_and_last_cooked(current_user.id)
            db.session.commit()

        return jsonify({"message": "Recipe and all associated cooking logs deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting recipe {recipe_id} and its logs: {e}")
        return jsonify({"error": "Failed to delete recipe and its logs"}), 500


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
        if 'ingredients' in data: 
             recipe.ingredients = data['ingredients']; updated = True
        if 'instructions' in data and data['instructions'] and recipe.instructions != data['instructions']:
            recipe.instructions = data['instructions']; updated = True
        if 'image' in data: 
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
        
        if recipe_to_share.user_id != current_user.id:
            return jsonify({"error": "You can only share your own recipes."}), 403

        existing_shared = SharedRecipe.query.filter_by(receiver_id=receiver_id, recipe_id=recipe_id).first() 
        if existing_shared: return jsonify({"error": "Recipe already shared with this user"}), 409
        
        new_shared = SharedRecipe(
            receiver_id=receiver_id,
            recipe_id=recipe_id,
            sharer_name=sharer_name,
            )
        db.session.add(new_shared); db.session.commit()
    except ValueError: return jsonify({"error": "Invalid ID format"}), 400
    except Exception as e:
        print(f"Error creating shared recipe: {e}"); db.session.rollback()
        return jsonify({"error": "Failed to create shared recipe"}), 500
    return jsonify({"message": f"Recipe {recipe_to_share.name} shared with {receiver_name} successfully."}), 201


@main.route('/api/shared_recipes/my', methods=['GET'])
@login_required
def get_my_shared_recipes():
    try:
        user_id = current_user.id
        shared_recipes_data = db.session.query(
                SharedRecipe.id,
                SharedRecipe.recipe_id,
                SharedRecipe.sharer_name,
                SharedRecipe.date_shared,
                Recipe.name.label('recipe_name') 
            ).join(Recipe, SharedRecipe.recipe_id == Recipe.id)\
            .filter(SharedRecipe.receiver_id == user_id)\
            .order_by(SharedRecipe.date_shared.desc())\
            .all()

        results = [
            {
                "id": sr.id,
                "recipe_id": sr.recipe_id,
                "sharer_name": sr.sharer_name,
                "date_shared": sr.date_shared.isoformat(), 
                "recipe_name": sr.recipe_name
            } for sr in shared_recipes_data
        ]
        return jsonify(results), 200
    except Exception as e:
        print(f"Error fetching shared recipes: {e}")
        return jsonify({"error": "Failed to fetch shared recipes"}), 500


@main.route('/users/search')
@login_required 
def user_search():
    q = request.args.get('q', '').strip()
    if len(q) < 2: return jsonify([])
    
    raw_matches = (db.session.query(User.username) 
                   .filter(User.username.ilike(f"%{q}%"))
                   .filter(User.id != current_user.id) 
                   .order_by(User.username).limit(5).all()) 
    
    usernames = [match[0] for match in raw_matches] 
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
    if user_to_add.id == current_user.id: 
        return jsonify({"message": "Owner already has full access."}), 200

    current_recipe_whitelist = list(recipe.whitelist) if recipe.whitelist is not None else []
    if user_to_add.id in current_recipe_whitelist:
        return jsonify({"message": f"User '{user_to_add.username}' is already in the whitelist"}), 200 
    
    current_recipe_whitelist.append(user_to_add.id)
    recipe.whitelist = current_recipe_whitelist 
    
    try:
        db.session.commit()
        sharer_name_for_share = current_user.username
        existing_shared_notification = SharedRecipe.query.filter_by(
            receiver_id=user_to_add.id, 
            recipe_id=recipe.id
        ).first()

        if not existing_shared_notification:
            new_shared_notification = SharedRecipe(
                receiver_id=user_to_add.id,
                recipe_id=recipe.id,
                sharer_name=sharer_name_for_share
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
    
    is_owner = (original_recipe.user_id == current_user.id)
    current_recipe_whitelist = original_recipe.whitelist if isinstance(original_recipe.whitelist, list) else []
    is_whitelisted = (current_user.id in current_recipe_whitelist)

    if not is_owner and not is_whitelisted:
        return jsonify({"error": "Unauthorized to clone this recipe"}), 403
    
    new_recipe = Recipe(
        name=f"{original_recipe.author.username}'s {original_recipe.name} (Clone)",
        category=original_recipe.category, time=original_recipe.time,
        ingredients=original_recipe.ingredients, 
        instructions=original_recipe.instructions,
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), 
        image=original_recipe.image, 
        user_id=current_user.id, 
        whitelist=[] 
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

@main.route('/log/<int:log_id>')
@login_required
def view_log_detail(log_id):
    log_entry = CookingLog.query.options(db.joinedload(CookingLog.recipe_logged))\
                                .filter_by(id=log_id).first_or_404()
    if log_entry.user_id != current_user.id:
        abort(403) 
    return render_template('view_log_detail.html', log_entry=log_entry, title='Cooking Log Details')


def calculate_user_stats(user_id):
    stats = {
        'total_sessions': 0,
        'most_frequent_recipe': {'name': '-', 'count': 0},
        'total_time_logged_seconds': 0, 
        'total_time_logged_hours': 0.0,
        'average_rating': 0.0, 
        'top_recipes_data': [], 
        'monthly_frequency_data': [],
        'top_recipes_this_month_data': [],
        'weekly_frequency_data': [],
        'top_rated_data': [],
        'top_rated_this_month_data': []
    }
    try:
        stats['total_sessions'] = CookingLog.query.filter_by(user_id=user_id).count()
        total_duration = db.session.query(func.sum(CookingLog.duration_seconds))\
                                  .filter(CookingLog.user_id == user_id, CookingLog.duration_seconds.isnot(None)).scalar()
        stats['total_time_logged_seconds'] = int(total_duration) if total_duration else 0
        stats['total_time_logged_hours'] = round(stats['total_time_logged_seconds'] / 3600, 2)
        avg_rating_query = db.session.query(func.avg(CookingLog.rating))\
                              .filter(CookingLog.user_id == user_id, CookingLog.rating.isnot(None)).scalar()
        stats['average_rating'] = float(avg_rating_query) if avg_rating_query is not None else 0.0

        top_recipes = (db.session.query(Recipe.name, func.count(CookingLog.id).label('log_count'))
                       .join(CookingLog, Recipe.id == CookingLog.recipe_id).filter(CookingLog.user_id == user_id)
                       .group_by(Recipe.name).order_by(desc('log_count')).limit(5).all())
        if top_recipes:
            stats['most_frequent_recipe'] = {'name': top_recipes[0][0], 'count': int(top_recipes[0][1])}
            stats['top_recipes_data'] = [{'name': name, 'count': int(count)} for name, count in top_recipes]
        
        today = date.today(); month_counts = {}
        for i in range(12):
            month_to_calc = today.month - i
            year_to_calc = today.year
            if month_to_calc <= 0:
                month_to_calc += 12
                year_to_calc -= 1
            month_counts[f"{year_to_calc:04d}-{month_to_calc:02d}"] = 0
        
        first_day_of_period = (today.replace(day=1) - timedelta(days=330)).replace(day=1)

        monthly_logs = (db.session.query(func.strftime('%Y-%m', CookingLog.date_cooked).label('month'),
                                        func.count(CookingLog.id).label('count'))
                        .filter(CookingLog.user_id == user_id, 
                                CookingLog.date_cooked >= first_day_of_period, 
                                CookingLog.date_cooked <= today) 
                        .group_by('month').order_by('month').all())
        
        for month_db, count in monthly_logs:
            if month_db in month_counts: 
                month_counts[month_db] = int(count)
        
        first_day_of_month = today.replace(day=1)
        top_recipes_month = (db.session.query(Recipe.name, func.count(CookingLog.id).label('log_count'))
                       .join(CookingLog, Recipe.id == CookingLog.recipe_id)
                       .filter(CookingLog.user_id == user_id,
                               CookingLog.date_cooked >= first_day_of_month)
                       .group_by(Recipe.name)
                       .order_by(desc('log_count'))
                       .limit(5).all())
        stats['top_recipes_this_month_data'] = [{'name': name, 'count': int(count)} for name, count in top_recipes_month]

        # Weekly Frequency Current Week (SQLite compatible)
        start_of_week = today - timedelta(days=today.weekday())  # Monday is the start of the week
        end_of_week = start_of_week + timedelta(days=6)
        weekly_counts = {day: 0 for day in range(1, 8)}  # Days 1 (Monday) to 7 (Sunday)
        weekly_logs = (db.session.query(func.strftime('%w', CookingLog.date_cooked).label('day_of_week'),
                                       func.count(CookingLog.id).label('count'))
                       .filter(CookingLog.user_id == user_id,
                               CookingLog.date_cooked >= start_of_week,
                               CookingLog.date_cooked <= end_of_week)
                       .group_by('day_of_week')
                       .all())
        
        # SQLite returns Sunday as 0, so adjust to make Monday 1 and Sunday 7
        day_mapping = {0: 7, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
        for day_of_week, count in weekly_logs:
            adjusted_day = day_mapping.get(int(day_of_week), 7)
            weekly_counts[adjusted_day] = int(count)
        stats['weekly_frequency_data'] = [{'day': d, 'count': weekly_counts[d]} for d in range(1, 8)]

        top_rated = (db.session.query(Recipe.name, func.avg(CookingLog.rating).label('avg_rating'))
                    .join(CookingLog, Recipe.id == CookingLog.recipe_id)
                    .filter(CookingLog.user_id == user_id,
                            CookingLog.rating.isnot(None))
                    .group_by(Recipe.name)
                    .order_by(desc('avg_rating'))
                    .limit(5).all())
        stats['top_rated_data'] = [{'name': name, 'rating': float(avg)} for name, avg in top_rated]

        top_rated_month = (db.session.query(Recipe.name, func.avg(CookingLog.rating).label('avg_rating'))
                         .join(CookingLog, Recipe.id == CookingLog.recipe_id)
                         .filter(CookingLog.user_id == user_id,
                                 CookingLog.rating.isnot(None),
                                 CookingLog.date_cooked >= first_day_of_month)
                         .group_by(Recipe.name)
                         .order_by(desc('avg_rating'))
                         .limit(5).all())
        stats['top_rated_this_month_data'] = [{'name': name, 'rating': float(avg)} for name, avg in top_rated_month]
        
        sorted_months = sorted(month_counts.keys()) 
        stats['monthly_frequency_data'] = [{'month': m, 'count': month_counts[m]} for m in sorted_months]

    except Exception as e: 
        print(f"Error calculating stats for user {user_id}: {e}")
    return stats

# --- End of File ---