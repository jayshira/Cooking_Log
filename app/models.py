import json
<<<<<<< Updated upstream
from datetime import datetime # Use datetime for proper timestamp handling
from . import db        # Import db instance from the current package (__init__.py)
from flask_login import UserMixin # Import UserMixin for Flask-Login integration
from . import bcrypt    # Import bcrypt instance from the current package (__init__.py)

# --- Recipe Model ---
=======
from . import db
from flask_login import UserMixin
from . import bcrypt
from datetime import date, datetime, timedelta # Import date/time modules

# --- Existing Recipe Model (Keep as is, just add relationship) ---
>>>>>>> Stashed changes
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
<<<<<<< Updated upstream
    time = db.Column(db.Integer, nullable=False) # Prep/Cook time in minutes
    ingredients_json = db.Column(db.Text, nullable=False) # Store ingredients as JSON string
    instructions = db.Column(db.Text, nullable=False)
    # Use DateTime type and default to current UTC time when a recipe is added
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image = db.Column(db.Text, nullable=True) # Store image as Base64 data URI or potentially a file path

    # --- Foreign Key Relationship to User ---
    # Defines the 'many' side of the one-to-many relationship (many Recipes belong to one User)
    # db.ForeignKey('user.id') links this column to the 'id' column in the 'user' table (lowercase table name).
    # nullable=False ensures every recipe must belong to a user.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # --- Ingredients Property ---
    # Provides a convenient way to get/set ingredients as a Python list,
    # while storing them as a JSON string in the database for efficiency.
=======
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

>>>>>>> Stashed changes
    @property
    def ingredients(self):
        """ Safely parses the ingredients_json string into a list. """
        if not self.ingredients_json:
            return []
        try:
            # Attempt to load directly as JSON list
            parsed = json.loads(self.ingredients_json)
            # Ensure the parsed result is actually a list
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
             # Fallback: If it's a string (perhaps legacy data), try splitting by comma
             # This part might be removed if you ensure data is always saved as JSON.
            if isinstance(self.ingredients_json, str):
                 # Split by comma, strip whitespace, and filter out empty strings
                 return [i.strip() for i in self.ingredients_json.split(',') if i.strip()]
        # Return an empty list if parsing fails or it's not a list/string
        return []

    @ingredients.setter
    def ingredients(self, value):
        """ Ensures ingredients are stored as a JSON string list. """
        if isinstance(value, list):
            # Directly dump the list to a JSON string
            self.ingredients_json = json.dumps(value)
        elif isinstance(value, str):
            # Convert comma-separated string to list, then dump to JSON
            # This handles input from simple text areas directly.
            cleaned_list = [i.strip() for i in value.split(',') if i.strip()]
            self.ingredients_json = json.dumps(cleaned_list)
        else:
            # Default to an empty JSON list if the input type is unexpected
            self.ingredients_json = json.dumps([])

    # --- to_dict Method ---
    # Useful for converting the Recipe object into a dictionary, often needed for API responses.
    def to_dict(self):
<<<<<<< Updated upstream
        """ Returns dictionary representation of the recipe. """
=======
        # Add user_id to the dictionary for potential frontend use
>>>>>>> Stashed changes
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'time': self.time,
            'ingredients': self.ingredients, # Use the property to get the parsed list
            'instructions': self.instructions,
            # Format the datetime object into a standard ISO string format
            'date': self.date_added.isoformat() + 'Z' if self.date_added else None, # Add Z for UTC
            'image': self.image,
<<<<<<< Updated upstream
            # Include the author's username using the backref relationship ('author' from User model)
            'author': self.author.username if self.author else 'Unknown',
            # Include user_id, might be useful on the frontend sometimes
            'user_id': self.user_id
=======
            'author': self.author.username if self.author else 'Unknown',
            'user_id': self.user_id # Add user_id
>>>>>>> Stashed changes
        }

    # --- __repr__ Method ---
    # Provides a developer-friendly string representation of the object, useful for debugging.
    def __repr__(self):
        return f"<Recipe {self.id}: {self.name}>"

<<<<<<< Updated upstream

# --- User Model ---
# Inherits from db.Model (SQLAlchemy base class) and UserMixin (Flask-Login requirement)
=======
# --- Updated User Model ---
>>>>>>> Stashed changes
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Store hashed password
    # Use DateTime type and default to current UTC time when a user joins
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

<<<<<<< Updated upstream
    # --- Relationship to Recipe ---
    # Defines the 'one' side of the one-to-many relationship (one User has many Recipes)
    # 'Recipe' is the class name of the related model.
    # backref='author' creates a virtual 'author' attribute on Recipe instances to access the related User.
    # lazy=True means SQLAlchemy loads the related recipes only when the 'recipes' attribute is accessed.
    # cascade="all, delete-orphan": If a User is deleted, all their associated Recipe records are also deleted.
    #   'delete-orphan' ensures recipes removed from user.recipes list are also deleted from DB.
    recipes = db.relationship('Recipe', backref='author', lazy=True, cascade="all, delete-orphan")

    # --- Password Hashing Methods ---
    def set_password(self, password):
        """Hashes the provided password using Bcrypt and stores the hash."""
        # Use the bcrypt instance initialized in app/__init__.py
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        # Ensure password_hash is not None before attempting to check
        if self.password_hash is None:
            return False
        # Use bcrypt's check function
=======
    # Relationship to Recipe (one-to-many) - Keep as is
    recipes = db.relationship('Recipe', backref='author', lazy=True)

    # --- Additions for Cooking Log ---
    # Relationship to CookingLog (one-to-many: User has many logs)
    # 'cook' is the attribute to access the User from a CookingLog instance
    # 'backref='logs'' adds a 'logs' attribute to the User object to get their logs
    cooking_logs = db.relationship('CookingLog', backref='cook', lazy=True)

    # Fields for cooking streak
    last_cooked_date = db.Column(db.Date, nullable=True)
    current_streak = db.Column(db.Integer, default=0, nullable=False)
    # --- End Additions ---

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
>>>>>>> Stashed changes
        return bcrypt.check_password_hash(self.password_hash, password)

    # --- __repr__ Method ---
    # Provides a developer-friendly string representation for debugging.
    def __repr__(self):
        return f"<User {self.username}>"

<<<<<<< Updated upstream
# --- Future Models ---
# Add other models (e.g., CookingLog, Tag, ShareLink) here later as needed.
=======
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
>>>>>>> Stashed changes
