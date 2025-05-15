# app/models.py
import json
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import UserMixin
from datetime import date, datetime, timedelta, timezone # Added timezone

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    ingredients_json = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(30), nullable=False) # Original creation/added date
    image = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    cooking_logs = db.relationship('CookingLog', backref='recipe_logged', lazy=True)
    
    # whitelist should default to an empty list
    whitelist = db.Column(db.JSON, default=lambda: [])

    @property
    def ingredients(self):
        if not self.ingredients_json: # Handle case where ingredients_json might be None or empty
            return []
        try:
            # Ensure that what's loaded is a list, filter if not.
            loaded_list = json.loads(self.ingredients_json)
            if isinstance(loaded_list, list):
                # Filter out empty strings or strings with only whitespace AFTER loading
                # This ensures the property always returns clean data
                return [item for item in loaded_list if isinstance(item, str) and item.strip()]
            else: # If it's not a list (e.g. was a single string incorrectly stored as JSON)
                return [loaded_list] if isinstance(loaded_list, str) and loaded_list.strip() else []
        except (json.JSONDecodeError, TypeError):
            # Fallback for when ingredients_json is not valid JSON but a simple comma-separated string
            if isinstance(self.ingredients_json, str):
                 return [i.strip() for i in self.ingredients_json.split(',') if i.strip()]
            return []

    @ingredients.setter
    def ingredients(self, value):
        if isinstance(value, list):
            # Filter empty/whitespace strings from the list before storing
            cleaned_list = [str(item).strip() for item in value if str(item).strip()]
            self.ingredients_json = json.dumps(cleaned_list)
        elif isinstance(value, str):
            # Split comma-separated string and filter empty/whitespace items
            cleaned_list = [i.strip() for i in value.split(',') if i.strip()]
            self.ingredients_json = json.dumps(cleaned_list)
        elif value is None: # Handle setting to None
             self.ingredients_json = json.dumps([])
        else:
            self.ingredients_json = json.dumps([])

    def to_dict(self):
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
            'user_id': self.user_id
        }

    def __repr__(self):
        return f"<Recipe {self.id}: {self.name}>"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Werkzeug hashes can be long. String(256) is a safe length.
    password_hash = db.Column(db.String(256), nullable=False)

    recipes = db.relationship('Recipe', backref='author', lazy=True)
    cooking_logs = db.relationship('CookingLog', backref='cook', lazy=True)

    last_cooked_date = db.Column(db.Date, nullable=True)
    current_streak = db.Column(db.Integer, default=0, nullable=False)

    def set_password(self, password):
        """Hashes the password using Werkzeug and stores it."""
        # generate_password_hash automatically handles salting.
        # Default method is 'scrypt' or 'pbkdf2:sha256' depending on Werkzeug version & system.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks the provided password against the stored Werkzeug hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class CookingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    date_cooked = db.Column(db.Date, nullable=False, default=date.today)
    duration_seconds = db.Column(db.Integer, nullable=True) 
    rating = db.Column(db.Integer, nullable=True) 
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    image_url = db.Column(db.Text, nullable=True) # Stores base64 encoded image or path

    def __repr__(self):
        recipe_name = self.recipe_logged.name if self.recipe_logged else 'Unknown Recipe'
        has_image_str = " (has image)" if self.image_url else ""
        return f"<CookingLog {self.id} for '{recipe_name}' by User {self.user_id} on {self.date_cooked}{has_image_str}>"

class SharedRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sharer_name = db.Column(db.String(80), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    date_shared = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        recipe = Recipe.query.get(self.recipe_id) 
        return {
            'id': self.id,
            'receiver_id': self.receiver_id,
            'recipe_id': self.recipe_id,
            'sharer_name': self.sharer_name,
            'date_shared': self.date_shared.isoformat(),
            'recipe_name': recipe.name if recipe else 'Unknown'
        }