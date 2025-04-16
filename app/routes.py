# app/routes.py
from flask import Blueprint, render_template, request, jsonify
# Import login_required and current_user
from flask_login import login_required, current_user
from .models import Recipe, User # Import User as well
from . import db

main = Blueprint('main', __name__)

# --- HTML Page Routes ---
@main.route('/')
def index():
    # Add logic to show login/signup or logout/dashboard links based on auth status
    return render_template('index.html', current_user=current_user)

# --- API Routes ---
@main.route('/api/recipes', methods=['GET'])
def get_recipes():
    """API endpoint to get all recipes (public for now, maybe filter later)."""
    try:
        # Optional: Filter recipes by user later if needed for a 'My Recipes' specific view
        # recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.id.desc()).all()
        recipes = Recipe.query.order_by(Recipe.id.desc()).all()
        return jsonify([recipe.to_dict() for recipe in recipes]), 200
    except Exception as e:
        print(f"Error fetching recipes: {e}")
        return jsonify({"error": "Failed to fetch recipes"}), 500

@main.route('/api/recipes', methods=['POST'])
@login_required # Protect this route - only logged-in users can add
def add_recipe():
    """API endpoint to add a new recipe (associated with current user)."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions', 'date']
    if not all(field in data and data[field] is not None for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        new_recipe = Recipe(
            name=data['name'],
            category=data['category'],
            time=int(data['time']),
            ingredients=data['ingredients'],
            instructions=data['instructions'],
            date=data['date'],
            image=data.get('image'),
            user_id=current_user.id # Associate with the logged-in user
            # or use backref: author=current_user
        )
        db.session.add(new_recipe)
        db.session.commit()
        return jsonify(new_recipe.to_dict()), 201
    except (ValueError, TypeError) as e:
        db.session.rollback()
        print(f"Error adding recipe (data issue): {e}")
        return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error adding recipe (database issue): {e}")
        return jsonify({"error": "Failed to add recipe"}), 500

@main.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_recipe_api(recipe_id):
    """API endpoint to delete a specific recipe by ID."""
    try:
        recipe = Recipe.query.get_or_404(recipe_id)

        # --- Authorization Check ---
        # Ensure the current user owns this recipe before deleting
        if recipe.user_id != current_user.id:
             return jsonify({"error": "Unauthorized to delete this recipe"}), 403 # 403 Forbidden

        db.session.delete(recipe)
        db.session.commit()
        return jsonify({"message": "Recipe deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to delete recipe"}), 500

# --- Add Placeholders for Future Protected Routes ---
# These routes don't exist yet, but show where @login_required would go

@main.route('/mykitchen')
@login_required
def my_kitchen():
    # Logic for the user's private kitchen view will go here
    return f"Welcome to your kitchen, {current_user.username}! (Page under construction)"

@main.route('/dashboard')
@login_required
def dashboard():
    # Logic for the user's dashboard/insights view will go here
    return f"Your dashboard, {current_user.username}! (Page under construction)"

@main.route('/share')
@login_required
def share():
    # Logic for the sharing management view will go here
    return f"Sharing center for {current_user.username}! (Page under construction)"
# --- Add any other routes as needed ---