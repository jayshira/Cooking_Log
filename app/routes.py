# app/routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import Recipe, User, CookingLog, SharedRecipe, db
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import func, desc
import base64 # For image encoding

# Import new forms
from .forms import UpdateProfileForm, ChangePasswordForm


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
    
    db.session.add(user)

# --- Helper for saving profile picture (similar to log image helper) ---
def save_profile_picture_helper(form_picture_data):
    if not form_picture_data:
        return None
    try:
        image_data = form_picture_data.read()
        
        if len(image_data) > 2 * 1024 * 1024: # Max 2MB for profile pic
            flash('Profile picture file is too large (max 2MB).', 'danger')
            return "ERROR_SIZE"

        if not form_picture_data.mimetype.startswith('image/'):
            flash('Invalid image file type. Please upload a valid image (JPEG, PNG, GIF).', 'danger')
            return "ERROR_TYPE"

        base64_image = base64.b64encode(image_data).decode('utf-8')
        return f"data:{form_picture_data.mimetype};base64,{base64_image}"
    except Exception as e:
        print(f"Error processing profile picture: {e}")
        flash('Could not process the uploaded profile picture.', 'danger')
        return "ERROR_PROCESSING"

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
        streak_display_value = 0

    stats = calculate_user_stats(user_id)

    return render_template('home.html',
                         recent_logs=recent_logs,
                         streak=streak_display_value,
                         log_stats=stats)

# --- NEW PROFILE ROUTE ---
@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    update_profile_form = UpdateProfileForm()
    change_password_form = ChangePasswordForm()

    if request.method == 'POST':
        if update_profile_form.submit_profile.data and update_profile_form.validate_on_submit():
            user_changed_flag = False # To track if any actual DB change is made
            if update_profile_form.username.data != current_user.username:
                current_user.username = update_profile_form.username.data
                user_changed_flag = True
            if update_profile_form.email.data != current_user.email:
                current_user.email = update_profile_form.email.data
                user_changed_flag = True
            
            if update_profile_form.profile_picture.data:
                picture_file = update_profile_form.profile_picture.data
                if picture_file and picture_file.filename: # Check if a file was actually uploaded
                    picture_file.seek(0) # Rewind stream in case it was read by a validator
                    saved_image_url = save_profile_picture_helper(picture_file)
                    
                    if saved_image_url and not saved_image_url.startswith("ERROR_"):
                        current_user.profile_image_url = saved_image_url
                        user_changed_flag = True
                    # If saved_image_url indicates an error, the helper function already flashed.
                    # No need to set user_changed_flag to True for a failed image update.
            
            if user_changed_flag:
                try:
                    db.session.commit()
                    flash('Your profile has been updated successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error updating profile: {str(e)}', 'danger')
            # else:
                # Optionally, flash "No changes were made." if desired, but often not necessary.
            return redirect(url_for('main.profile'))

        elif change_password_form.submit_password.data and change_password_form.validate_on_submit():
            if current_user.check_password(change_password_form.current_password.data):
                current_user.set_password(change_password_form.new_password.data)
                try:
                    db.session.commit()
                    flash('Your password has been changed successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error changing password: {str(e)}', 'danger')
                return redirect(url_for('main.profile'))
            else:
                flash('Incorrect current password.', 'danger')
        # If form validation fails, the template will re-render with errors displayed.
    
    # For GET requests or if POST validation failed, pre-populate the update_profile_form
    update_profile_form.username.data = current_user.username
    update_profile_form.email.data = current_user.email
    # Note: FileField (profile_picture) is not pre-filled with existing image data for updates.
    
    return render_template('profile.html', title='My Profile',
                           update_profile_form=update_profile_form,
                           change_password_form=change_password_form,
                           user=current_user)


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
    is_owner = (recipe.user_id == current_user.id)
    current_recipe_whitelist = recipe.whitelist if isinstance(recipe.whitelist, list) else []
    is_whitelisted = (current_user.id in current_recipe_whitelist)

    if not is_owner and not is_whitelisted:
         flash('You do not have permission to start a cooking session for this recipe.', 'warning')
         return redirect(url_for('main.view_recipe', recipe_id=recipe.id))

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
                if len(image_data) > 5 * 1024 * 1024:
                    flash('Image file is too large (max 5MB).', 'danger')
                    return redirect(url_for('main.start_cooking_session', recipe_id=recipe.id))

                base64_image = base64.b64encode(image_data).decode('utf-8')
                log_image_url = f"data:{image_file.mimetype};base64,{base64_image}"
            except Exception as img_e:
                print(f"Error processing log image: {img_e}")
                flash('Could not process the uploaded image.', 'danger')

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
        
        _recalculate_user_streak_and_last_cooked(current_user.id)

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
        return redirect(url_for('main.view_logs'))

    if request.method == 'POST':
        try:
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
            
            db.session.commit()

            _recalculate_user_streak_and_last_cooked(current_user.id)
            db.session.commit()

            flash('Cooking log updated successfully!', 'success')
            return redirect(url_for('main.view_log_detail', log_id=log_entry.id))

        except Exception as e:
            db.session.rollback()
            print(f"Error updating log (ID: {log_id}): {e}")
            flash(f'An error occurred while updating the log: {str(e)}', 'danger')

    return render_template('edit_log.html', log_entry=log_entry, title='Edit Cooking Log')



# --- API Routes ---
@main.route('/api/recipes', methods=['GET'])
@login_required
def get_recipes():
    try:
        if not current_user or not current_user.is_authenticated:
            print("[ERROR] /api/recipes: User not authenticated or current_user is None.")
            return jsonify({"error": "User not authenticated"}), 401

        print(f"[DEBUG] /api/recipes: Fetching recipes for user_id: {current_user.id}")
        recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.id.desc()).all()
        print(f"[DEBUG] /api/recipes: Found {len(recipes)} recipes for user_id: {current_user.id}")

        recipes_data = []
        for i, recipe in enumerate(recipes):
            try:
                recipe_dict = recipe.to_dict()
                recipes_data.append(recipe_dict)
                # Optional: print first few dicts to check structure
                # if i < 2:
                #     print(f"[DEBUG] /api/recipes: Recipe dict {i}: {recipe_dict}")
            except Exception as e_to_dict:
                print(f"[ERROR] /api/recipes: Failed to convert recipe ID {recipe.id} ('{recipe.name}') to dict for user_id {current_user.id}. Error: {e_to_dict}")
                # Fallback: add a minimal representation or skip
                recipes_data.append({'id': recipe.id, 'name': recipe.name, 'error': 'Serialization failed', 'original_error': str(e_to_dict)})
        
        # print(f"[DEBUG] /api/recipes: Final recipes_data to be_jsonified: {recipes_data}")
        return jsonify(recipes_data), 200
    except Exception as e:
        print(f"[CRITICAL ERROR] /api/recipes (user_id: {current_user.id if current_user and current_user.is_authenticated else 'UNKNOWN'}): {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch recipes due to a server error", "details": str(e)}), 500

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

        logs_to_delete = CookingLog.query.filter_by(recipe_id=recipe_to_delete.id).all()
        for log in logs_to_delete:
            db.session.delete(log)
        
        shared_entries_to_delete = SharedRecipe.query.filter_by(recipe_id=recipe_to_delete.id).all()
        for shared_entry in shared_entries_to_delete:
            db.session.delete(shared_entry)

        db.session.delete(recipe_to_delete)
        db.session.commit()
        
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
            recipe.image = data['image']; updated = True # Allows setting image to null/empty string to remove it
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
    required_fields = ['receiver_name', 'recipe_id'] # receiver_name should be username
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields (receiver_name, recipe_id)"}), 400
    try:
        sharer_name = current_user.username # Use current_user's username
        receiver_username = str(data['receiver_name'])
        recipe_id = int(data['recipe_id'])

        receiver_user = User.query.filter_by(username=receiver_username).first()
        if not receiver_user:
            return jsonify({"error": f"Receiver user '{receiver_username}' not found"}), 404
        
        if receiver_user.id == current_user.id:
            return jsonify({"error": "Cannot share a recipe with yourself."}), 400

        recipe_to_share = Recipe.query.get(recipe_id)
        if not recipe_to_share:
            return jsonify({"error": "Recipe not found"}), 404
        
        if recipe_to_share.user_id != current_user.id:
            return jsonify({"error": "You can only share your own recipes."}), 403

        existing_shared = SharedRecipe.query.filter_by(
            receiver_id=receiver_user.id, 
            recipe_id=recipe_id
        ).first()
        if existing_shared:
            return jsonify({"message": "Recipe already shared with this user"}), 200 # Or 409 if you prefer error

        new_shared = SharedRecipe(
            receiver_id=receiver_user.id,
            recipe_id=recipe_id,
            sharer_name=sharer_name, # Store the sharer's username
            )
        db.session.add(new_shared)
        db.session.commit()

        # Also add to whitelist if not already there
        current_recipe_whitelist = list(recipe_to_share.whitelist) if recipe_to_share.whitelist is not None else []
        if receiver_user.id not in current_recipe_whitelist:
            current_recipe_whitelist.append(receiver_user.id)
            recipe_to_share.whitelist = current_recipe_whitelist
            db.session.commit()

    except ValueError:
        return jsonify({"error": "Invalid recipe ID format"}), 400
    except Exception as e:
        print(f"Error creating shared recipe: {e}"); db.session.rollback()
        return jsonify({"error": "Failed to share recipe due to a server error"}), 500
    
    return jsonify({"message": f"Recipe '{recipe_to_share.name}' shared with {receiver_username} successfully."}), 201


# app/routes.py
# ... (other imports)
from .models import Recipe, User, CookingLog, SharedRecipe, db # Ensure User is imported
# ...

@main.route('/api/shared_recipes/my', methods=['GET'])
@login_required
def get_my_shared_recipes():
    try:
        user_id = current_user.id
        
        # Query to get shared recipes and join with Recipe for recipe_name
        # Then, for each result, fetch the sharer's profile picture
        shared_recipes_base = db.session.query(
                SharedRecipe.id,
                SharedRecipe.recipe_id,
                SharedRecipe.sharer_name,
                SharedRecipe.date_shared,
                Recipe.name.label('recipe_name')
            ).join(Recipe, SharedRecipe.recipe_id == Recipe.id)\
            .filter(SharedRecipe.receiver_id == user_id)\
            .order_by(SharedRecipe.date_shared.desc())\
            .all()

        results = []
        for sr_base in shared_recipes_base:
            sharer_user = User.query.filter_by(username=sr_base.sharer_name).first()
            sharer_profile_image_url = sharer_user.profile_image_url if sharer_user else None
            
            results.append({
                "id": sr_base.id,
                "recipe_id": sr_base.recipe_id,
                "sharer_name": sr_base.sharer_name,
                "date_shared": sr_base.date_shared.isoformat(),
                "recipe_name": sr_base.recipe_name,
                "sharer_profile_image_url": sharer_profile_image_url # New field
            })
            
        return jsonify(results), 200
    except Exception as e:
        print(f"Error fetching shared recipes for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch shared recipes"}), 500


@main.route('/users/search')
@login_required
def user_search():
    q = request.args.get('q', '').strip()
    if len(q) < 1: # Allow search for 1 character if desired, adjust if needed
        return jsonify([])
    
    # Exclude current user from search results
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
    if not data or "username" not in data:
        return jsonify({"error": "Username missing in request body"}), 400

    username_to_whitelist = str(data.get("username", "")).strip()
    if not username_to_whitelist:
        return jsonify({"error": "Username cannot be empty"}), 400
    
    user_to_add = User.query.filter(User.username == username_to_whitelist).first()
    if not user_to_add:
        return jsonify({"error": f"User '{username_to_whitelist}' not found"}), 404
    
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to manage whitelist for this recipe"}), 403
    
    if user_to_add.id == current_user.id:
        return jsonify({"message": "As the owner, you already have full access."}), 200 # Or 400 if considered an error

    current_recipe_whitelist = list(recipe.whitelist) if recipe.whitelist is not None else []
    if user_to_add.id in current_recipe_whitelist:
        return jsonify({"message": f"User '{user_to_add.username}' is already in the whitelist"}), 200 # Or 409
    
    current_recipe_whitelist.append(user_to_add.id)
    recipe.whitelist = current_recipe_whitelist
    
    try:
        # Create a SharedRecipe notification entry
        existing_shared_notification = SharedRecipe.query.filter_by(
            receiver_id=user_to_add.id,
            recipe_id=recipe.id
        ).first()

        if not existing_shared_notification:
            new_shared_notification = SharedRecipe(
                receiver_id=user_to_add.id,
                recipe_id=recipe.id,
                sharer_name=current_user.username # Sharer is the current user (owner)
            )
            db.session.add(new_shared_notification)
        
        db.session.commit()
            
        # shared_url = url_for('main.view_recipe', recipe_id=recipe.id, _external=True) # Link not strictly needed in API response
        return jsonify({"message": f"Recipe '{recipe.name}' access granted to {user_to_add.username}."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating whitelist/shared_recipe for recipe {recipe.id}: {e}")
        return jsonify({"error": "Failed to update whitelist due to a server error"}), 500


@main.route("/recipes/clonerecipe", methods=["POST"])
@login_required
def clone_recipe():
    data = request.get_json()
    if not data or "recipe_id" not in data:
        return jsonify({"error": "Recipe ID missing"}), 400
    
    recipe_id_to_clone = data.get("recipe_id")
    try:
        recipe_id_to_clone = int(recipe_id_to_clone)
    except ValueError:
        return jsonify({"error": "Invalid Recipe ID format"}), 400

    original_recipe = db.session.get(Recipe, recipe_id_to_clone)
    if not original_recipe:
        return jsonify({"error": "Original recipe not found"}), 404
    
    is_owner = (original_recipe.user_id == current_user.id)
    current_recipe_whitelist = original_recipe.whitelist if isinstance(original_recipe.whitelist, list) else []
    is_whitelisted = (current_user.id in current_recipe_whitelist)

    if not is_owner and not is_whitelisted:
        return jsonify({"error": "Unauthorized to clone this recipe"}), 403
    
    # Determine the author's username for the clone's name
    author_username = original_recipe.author.username if original_recipe.author else "Original"

    new_recipe = Recipe(
        name=f"{author_username}'s {original_recipe.name} (Clone)",
        category=original_recipe.category, time=original_recipe.time,
        ingredients=list(original_recipe.ingredients) if original_recipe.ingredients else [], # Ensure it's a new list
        instructions=original_recipe.instructions,
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        image=original_recipe.image, # Can share the same image URL or implement image duplication
        user_id=current_user.id,
        whitelist=[] # Cloned recipe starts with an empty whitelist for the new owner
    )
    try:
        db.session.add(new_recipe)
        db.session.commit()
        return jsonify({"message": f"Recipe '{original_recipe.name}' cloned successfully to your kitchen!",
                        "new_recipe_id": new_recipe.id }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error cloning recipe {original_recipe.id}: {e}")
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
                                .filter_by(id=log_id, user_id=current_user.id).first_or_404()
    # No need for if log_entry.user_id != current_user.id:, as filter_by already handles it with first_or_404
    return render_template('view_log_detail.html', log_entry=log_entry, title='Cooking Log Details')


def calculate_user_stats(user_id):
    stats = {
        'total_sessions': 0,
        'most_frequent_recipe': {'name': '-', 'count': 0},
        'total_time_logged_seconds': 0,
        'total_time_logged_hours': 0.0, # Not used in JS, but kept for consistency
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
        
        total_duration_result = db.session.query(func.sum(CookingLog.duration_seconds))\
                                  .filter(CookingLog.user_id == user_id, CookingLog.duration_seconds.isnot(None)).scalar()
        stats['total_time_logged_seconds'] = int(total_duration_result) if total_duration_result is not None else 0
        
        avg_rating_result = db.session.query(func.avg(CookingLog.rating))\
                              .filter(CookingLog.user_id == user_id, CookingLog.rating.isnot(None)).scalar()
        stats['average_rating'] = float(avg_rating_result) if avg_rating_result is not None else 0.0

        top_recipes = (db.session.query(Recipe.name, func.count(CookingLog.id).label('log_count'))
                       .join(CookingLog, Recipe.id == CookingLog.recipe_id)
                       .filter(CookingLog.user_id == user_id)
                       .group_by(Recipe.name).order_by(desc('log_count')).limit(5).all())
        if top_recipes:
            stats['most_frequent_recipe'] = {'name': top_recipes[0][0], 'count': int(top_recipes[0][1])}
            stats['top_recipes_data'] = [{'name': name, 'count': int(count)} for name, count in top_recipes]
        
        today = datetime.now(PERTH_TZ).date() # Use Perth timezone for consistency
        month_counts = {}
        # Initialize for the last 12 months including current
        for i in range(12):
            # Calculate year and month for the i-th month ago
            year_to_calc = today.year
            month_to_calc = today.month - i
            while month_to_calc <= 0:
                month_to_calc += 12
                year_to_calc -= 1
            month_counts[f"{year_to_calc:04d}-{month_to_calc:02d}"] = 0
        
        # Define the start of the 12-month period for querying logs
        first_day_of_12_month_period = (today.replace(day=1) - timedelta(days=365*0 + 30*11)).replace(day=1) # A simpler way to get ~12 months ago
        
        monthly_logs = (db.session.query(func.strftime('%Y-%m', CookingLog.date_cooked).label('month_year_str'),
                                        func.count(CookingLog.id).label('count'))
                        .filter(CookingLog.user_id == user_id,
                                CookingLog.date_cooked >= first_day_of_12_month_period,
                                CookingLog.date_cooked <= today)
                        .group_by('month_year_str').all()) # Order later in Python for full 12-month range
        
        for month_year_str_db, count_db in monthly_logs:
            if month_year_str_db in month_counts: # Ensure the month from DB is in our initialized dict
                month_counts[month_year_str_db] = int(count_db)
        
        stats['monthly_frequency_data'] = [{'month': m, 'count': month_counts[m]} for m in sorted(month_counts.keys())]


        first_day_of_current_month = today.replace(day=1)
        top_recipes_month = (db.session.query(Recipe.name, func.count(CookingLog.id).label('log_count'))
                       .join(CookingLog, Recipe.id == CookingLog.recipe_id)
                       .filter(CookingLog.user_id == user_id,
                               CookingLog.date_cooked >= first_day_of_current_month,
                               CookingLog.date_cooked <= today) # Ensure logs are up to today
                       .group_by(Recipe.name)
                       .order_by(desc('log_count'))
                       .limit(5).all())
        stats['top_recipes_this_month_data'] = [{'name': name, 'count': int(count)} for name, count in top_recipes_month]

        # Weekly frequency: Sunday=0, Monday=1, ..., Saturday=6 for strftime('%w')
        # Adjust to Mon=1...Sun=7 for consistency or direct use
        start_of_current_week = today - timedelta(days=today.weekday()) # weekday(): Mon=0..Sun=6
        end_of_current_week = start_of_current_week + timedelta(days=6)
        
        # Initialize counts for days 0 (Sun) to 6 (Sat) as per strftime('%w')
        weekly_counts_from_db = {str(i): 0 for i in range(7)} # Sunday (0) to Saturday (6)
        
        weekly_logs = (db.session.query(func.strftime('%w', CookingLog.date_cooked).label('day_of_week_str'), # SQLite's %w is 0 for Sunday
                                       func.count(CookingLog.id).label('count'))
                       .filter(CookingLog.user_id == user_id,
                               CookingLog.date_cooked >= start_of_current_week,
                               CookingLog.date_cooked <= end_of_current_week)
                       .group_by('day_of_week_str') # Group by the string result of strftime
                       .all())
        
        for day_of_week_str_db, count_db in weekly_logs:
            if day_of_week_str_db in weekly_counts_from_db:
                weekly_counts_from_db[day_of_week_str_db] = int(count_db)

        # Map to desired JS format: Sun, Mon, Tue, Wed, Thu, Fri, Sat
        # JS chart might expect days in a specific order, e.g., Sun-Sat or Mon-Sun
        # For the JS: Sun (day 0 in DB) should be first if chart expects Sun as start
        # The JS `updateWeeklyFrequencyChart` uses `days = ['Sun', 'Mon', ..., 'Sat']` and `item.day`
        # Let's make `item.day` 0-indexed for Sun-Sat to match typical array indexing
        stats['weekly_frequency_data'] = [
            {'day': 0, 'count': weekly_counts_from_db.get('0', 0)}, # Sunday
            {'day': 1, 'count': weekly_counts_from_db.get('1', 0)}, # Monday
            {'day': 2, 'count': weekly_counts_from_db.get('2', 0)}, # Tuesday
            {'day': 3, 'count': weekly_counts_from_db.get('3', 0)}, # Wednesday
            {'day': 4, 'count': weekly_counts_from_db.get('4', 0)}, # Thursday
            {'day': 5, 'count': weekly_counts_from_db.get('5', 0)}, # Friday
            {'day': 6, 'count': weekly_counts_from_db.get('6', 0)}  # Saturday
        ]


        top_rated = (db.session.query(Recipe.name, func.avg(CookingLog.rating).label('avg_rating'))
                    .join(CookingLog, Recipe.id == CookingLog.recipe_id)
                    .filter(CookingLog.user_id == user_id,
                            CookingLog.rating.isnot(None))
                    .group_by(Recipe.name)
                    .order_by(desc('avg_rating'), Recipe.name) # Secondary sort for consistent ordering on ties
                    .limit(5).all())
        stats['top_rated_data'] = [{'name': name, 'rating': round(float(avg),1) if avg is not None else 0.0} for name, avg in top_rated]

        top_rated_month = (db.session.query(Recipe.name, func.avg(CookingLog.rating).label('avg_rating'))
                         .join(CookingLog, Recipe.id == CookingLog.recipe_id)
                         .filter(CookingLog.user_id == user_id,
                                 CookingLog.rating.isnot(None),
                                 CookingLog.date_cooked >= first_day_of_current_month,
                                 CookingLog.date_cooked <= today)
                         .group_by(Recipe.name)
                         .order_by(desc('avg_rating'), Recipe.name)
                         .limit(5).all())
        stats['top_rated_this_month_data'] = [{'name': name, 'rating': round(float(avg),1) if avg is not None else 0.0} for name, avg in top_rated_month]
        
    except Exception as e:
        print(f"Error calculating stats for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
    return stats

# --- End of File ---