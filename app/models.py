# app/models.py
import json
from . import db
from flask_login import UserMixin # Import UserMixin
from . import bcrypt # Import bcrypt instance we will create in __init__

# Keep your existing Recipe model here...
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    ingredients_json = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(30), nullable=False)
    image = db.Column(db.Text, nullable=True)

    # Add relationship to User (one-to-many: User has many Recipes)
    # 'author' is the attribute to access the User object from a Recipe instance
    # 'backref='recipes'' adds a 'recipes' attribute to the User object to get their recipes
    # lazy=True means SQLAlchemy loads the related objects only when accessed
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


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
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'time': self.time,
            'ingredients': self.ingredients,
            'instructions': self.instructions,
            'date': self.date,
            'image': self.image,
            # Include author username in dict (optional)
            'author': self.author.username if self.author else 'Unknown'
        }

    def __repr__(self):
        return f"<Recipe {self.id}: {self.name}>"


# --- New User Model ---
class User(UserMixin, db.Model): # Inherit from UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationship to Recipe (one-to-many)
    # 'author' matches the backref used in Recipe model
    recipes = db.relationship('Recipe', backref='author', lazy=True)

    def set_password(self, password):
        """Hashes the password and stores it."""
        # Use the bcrypt instance initialized in __init__.py
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        """String representation for debugging."""
        return f"<User {self.username}>"

# Add other models (CookingLog, Tag, Share) here later