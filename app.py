# app.py
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import json # To handle ingredients list potentially

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'recipes.db')

app = Flask(__name__,
            static_folder='static',       # Serve static files from 'static' folder
            template_folder='templates')  # Look for templates in 'templates' folder

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable modification tracking

db = SQLAlchemy(app)

# --- Database Model ---
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Auto-incrementing ID
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    # Store ingredients as a JSON string for flexibility
    ingredients_json = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(30), nullable=False) # Store as ISO string
    # Store image as Base64 Data URL (can get large!)
    image = db.Column(db.Text, nullable=True)

    @property
    def ingredients(self):
        """Getter to return ingredients as a list."""
        try:
            return json.loads(self.ingredients_json)
        except (json.JSONDecodeError, TypeError):
            # Handle cases where it might not be valid JSON or None
            # Fallback for older data possibly stored as comma-separated string
            if isinstance(self.ingredients_json, str):
                return [i.strip() for i in self.ingredients_json.split(',') if i.strip()]
            return []

    @ingredients.setter
    def ingredients(self, value):
        """Setter to store ingredients list as JSON string."""
        if isinstance(value, list):
            self.ingredients_json = json.dumps(value)
        elif isinstance(value, str):
            # Basic handling if a comma-separated string is passed
            self.ingredients_json = json.dumps([i.strip() for i in value.split(',') if i.strip()])
        else:
             self.ingredients_json = json.dumps([]) # Default to empty list

    def to_dict(self):
        """Convert Recipe object to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'time': self.time,
            'ingredients': self.ingredients, # Use the property getter
            'instructions': self.instructions,
            'date': self.date,
            'image': self.image
        }

# --- Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """API endpoint to get all recipes."""
    try:
        recipes = Recipe.query.order_by(Recipe.id.desc()).all()
        return jsonify([recipe.to_dict() for recipe in recipes]), 200
    except Exception as e:
        print(f"Error fetching recipes: {e}")
        return jsonify({"error": "Failed to fetch recipes"}), 500


@app.route('/api/recipes', methods=['POST'])
def add_recipe():
    """API endpoint to add a new recipe."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Basic validation (can be more robust)
    required_fields = ['name', 'category', 'time', 'ingredients', 'instructions', 'date']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        new_recipe = Recipe(
            name=data['name'],
            category=data['category'],
            time=int(data['time']),
            ingredients=data['ingredients'], # Use the setter which handles JSON conversion
            instructions=data['instructions'],
            date=data['date'],
            image=data.get('image') # Optional image
        )
        db.session.add(new_recipe)
        db.session.commit()
        return jsonify(new_recipe.to_dict()), 201 # Return created recipe with its ID
    except (ValueError, TypeError) as e:
         db.session.rollback()
         print(f"Error adding recipe (data issue): {e}")
         return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error adding recipe (database issue): {e}")
        return jsonify({"error": "Failed to add recipe"}), 500


@app.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
def delete_recipe_api(recipe_id):
    """API endpoint to delete a recipe."""
    try:
        recipe = Recipe.query.get(recipe_id)
        if recipe is None:
            return jsonify({"error": "Recipe not found"}), 404

        db.session.delete(recipe)
        db.session.commit()
        return jsonify({"message": "Recipe deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to delete recipe"}), 500

# --- Initialize Database ---
def init_db():
    """Creates the database tables if they don't exist."""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created (if they didn't exist).")

# --- Run Application ---
if __name__ == '__main__':
    init_db() # Ensure database and tables exist before running
    app.run(debug=True) # debug=True for development (auto-reloads)