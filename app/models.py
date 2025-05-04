# app/models.py
import json
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import UserMixin
from datetime import date, datetime, timedelta

# --- Existing Recipe Model (Keep as is, just add relationship) ---
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    time = db.Column(db.Integer, nullable=False) # Assuming this is prep/cook time in minutes
    ingredients_json = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(30), nullable=False) # Original creation/added date
    image = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Add relationship to CookingLog
    # 'recipe_cooked' is the attribute to access the Recipe from a CookingLog instance
    # 'backref='logs'' adds a 'logs' attribute to the Recipe object to get its logs
    cooking_logs = db.relationship('CookingLog', backref='recipe_logged', lazy=True)

    # Added whitelisted user_id to the Recipe model
    whitelist = db.Column(db.JSON, default=list)

    @property
    def ingredients(self):
        try:
            return json.loads(self.ingredients_json)
        except (json.JSONDecodeError, TypeError):
            if isinstance(self.ingredients_json, str):
                 return [i.strip() for i in self.ingredients_json.split(',') if i.strip()]
            return []

    @ingredients.setter
    def ingredients(self, value):
        if isinstance(value, list):
            self.ingredients_json = json.dumps(value)
        elif isinstance(value, str):
            cleaned_list = [i.strip() for i in value.split(',') if i.strip()]
            self.ingredients_json = json.dumps(cleaned_list)
        else:
            self.ingredients_json = json.dumps([])

    def to_dict(self):
        # Add user_id to the dictionary for potential frontend use
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'time': self.time,
            'ingredients': self.ingredients,
            'instructions': self.instructions,
            'date': self.date,
            'image': self.image,
            'author': self.author.username if self.author else 'Unknown',
            'user_id': self.user_id # Add user_id
        }

    def __repr__(self):
        return f"<Recipe {self.id}: {self.name}>"

# --- Updated User Model ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Password hash column remains the same, Werkzeug hashes are typically longer though
    # Consider increasing length if needed in future, e.g., String(256)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationships (Remain the same)
    recipes = db.relationship('Recipe', backref='author', lazy=True)
    cooking_logs = db.relationship('CookingLog', backref='cook', lazy=True)

    # Streak Fields (Remain the same)
    last_cooked_date = db.Column(db.Date, nullable=True)
    current_streak = db.Column(db.Integer, default=0, nullable=False)

    def set_password(self, password):
        """Hashes the password using Werkzeug and stores it."""
        # generate_password_hash automatically handles salting
        # Default method is generally good (pbkdf2:sha256)
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks the provided password against the stored Werkzeug hash."""
        return check_password_hash(self.password_hash, password)
    # --- End Modified Password Methods ---

    def __repr__(self):
        return f"<User {self.username}>"

# --- New CookingLog Model ---
class CookingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    date_cooked = db.Column(db.Date, nullable=False, default=date.today)
    duration_seconds = db.Column(db.Integer, nullable=True) # Actual time spent cooking in seconds
    rating = db.Column(db.Integer, nullable=True) # e.g., 1-5 stars
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Track when the log entry was created

    # Relationships are defined via backref in User and Recipe models

    def __repr__(self):
        # Access related recipe name using the backref 'recipe_logged'
        recipe_name = self.recipe_logged.name if self.recipe_logged else 'Unknown Recipe'
        return f"<CookingLog {self.id} for '{recipe_name}' by User {self.user_id} on {self.date_cooked}>"