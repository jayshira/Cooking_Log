# app/models.py
import json
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import UserMixin
from datetime import date, datetime, timedelta, timezone # Added timezone

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    ingredients_json = db.Column(db.Text, nullable=False, default=lambda: json.dumps([]))
    instructions = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(30), nullable=False)
    image = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # The relationship from Recipe to User (many-to-one)
    # The backref 'recipes' on User.recipes will create an 'author' attribute here implicitly.
    # Or, define it explicitly without a conflicting backref:
    # author = db.relationship('User') # If User.recipes defines backref='author'
    # For clarity, if User.recipes defines backref='author', then this 'author' field is created by that.
    # If you want to define the relationship from Recipe's side primarily:
   

    cooking_logs = db.relationship('CookingLog', backref='recipe_logged', lazy=True)
    whitelist = db.Column(db.JSON, default=lambda: [])

    @property
    def ingredients(self):
        if not self.ingredients_json:
            return []
        try:
            loaded_list = json.loads(self.ingredients_json)
            if isinstance(loaded_list, list):
                return [item for item in loaded_list if isinstance(item, str) and item.strip()]
            else:
                return [loaded_list] if isinstance(loaded_list, str) and loaded_list.strip() else []
        except (json.JSONDecodeError, TypeError):
            if isinstance(self.ingredients_json, str):
                 return [i.strip() for i in self.ingredients_json.split(',') if i.strip()]
            return []

    @ingredients.setter
    def ingredients(self, value):
        if isinstance(value, list):
            cleaned_list = [str(item).strip() for item in value if str(item).strip()]
            self.ingredients_json = json.dumps(cleaned_list)
        elif isinstance(value, str):
            cleaned_list = [i.strip() for i in value.split(',') if i.strip()]
            self.ingredients_json = json.dumps(cleaned_list)
        elif value is None:
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
    password_hash = db.Column(db.String(256), nullable=False)
    profile_image_url = db.Column(db.Text, nullable=True)
    date_joined = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # This defines that a User can have many Recipes.
    # The backref='author' will create a 'User' object accessible as 'recipe.author' on the Recipe model.
    recipes = db.relationship('Recipe', backref='author', lazy=True) # This is correct and sufficient.

    cooking_logs = db.relationship('CookingLog', backref='cook', lazy=True)

    last_cooked_date = db.Column(db.Date, nullable=True)
    current_streak = db.Column(db.Integer, default=0, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

# ... (rest of the models.py file: CookingLog, SharedRecipe)
class CookingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    date_cooked = db.Column(db.Date, nullable=False, default=date.today)
    duration_seconds = db.Column(db.Integer, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    image_url = db.Column(db.Text, nullable=True)

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
        recipe = db.session.get(Recipe, self.recipe_id)
        return {
            'id': self.id,
            'receiver_id': self.receiver_id,
            'recipe_id': self.recipe_id,
            'sharer_name': self.sharer_name,
            'date_shared': self.date_shared.isoformat(),
            'recipe_name': recipe.name if recipe else 'Unknown'
        }