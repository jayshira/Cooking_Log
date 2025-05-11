# tests/test_models.py
import unittest
from app import create_app, db
from app.models import User, Recipe, CookingLog
from config import TestConfig
from datetime import date, datetime, timedelta, timezone # Ensure timezone is imported
from sqlalchemy.exc import IntegrityError

class BaseModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

# ... (UserModelCase and RecipeModelCase remain the same as the previous correct version) ...
class UserModelCase(BaseModelCase): 
    def test_password_hashing(self):
        u = User(username='susan', email='susan@example.com')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_create_user(self):
        u = User(username='john', email='john@example.com')
        u.set_password('dog')
        db.session.add(u)
        db.session.commit()
        retrieved_user = User.query.filter_by(username='john').first()
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.email, 'john@example.com')

    def test_password_hashing_edge_cases(self):
        u = User(username='testuser', email='test@example.com')
        u.set_password('')
        self.assertTrue(u.check_password(''))
        self.assertFalse(u.check_password('a'))
        long_password = 'a' * 1000
        u.set_password(long_password)
        self.assertTrue(u.check_password(long_password))
        self.assertFalse(u.check_password(long_password + 'b'))

    def test_user_uniqueness(self):
        u1 = User(username='uniqueuser', email='unique@example.com')
        u1.set_password('password')
        db.session.add(u1)
        db.session.commit()
        u2_same_username = User(username='uniqueuser', email='other@example.com')
        u2_same_username.set_password('password')
        db.session.add(u2_same_username)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        u3_same_email = User(username='otheruser', email='unique@example.com')
        u3_same_email.set_password('password')
        db.session.add(u3_same_email)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_streak_same_day_log(self):
        user = User(username='streakuser', email='streak@example.com')
        user.set_password('pass')
        user.last_cooked_date = date(2024, 5, 10)
        user.current_streak = 3
        db.session.add(user)
        db.session.commit()
        log_date_same = date(2024, 5, 10)
        if user.last_cooked_date:
            days_diff = (log_date_same - user.last_cooked_date).days
            if days_diff == 1: user.current_streak += 1
            elif days_diff == 0: pass
            elif days_diff > 1: user.current_streak = 1
        if user.last_cooked_date is None or log_date_same >= user.last_cooked_date:
             user.last_cooked_date = log_date_same
        db.session.commit()
        self.assertEqual(user.current_streak, 3)
        self.assertEqual(user.last_cooked_date, date(2024, 5, 10))

    def test_user_streak_logging_past_date_no_impact(self):
        user = User(username='pastloguser', email='pastlog@example.com')
        user.set_password('pass')
        user.last_cooked_date = date(2024, 5, 10)
        user.current_streak = 5
        db.session.add(user)
        db.session.commit()
        log_date_past = date(2024, 5, 8)
        if user.last_cooked_date is None or log_date_past >= user.last_cooked_date:
            user.last_cooked_date = log_date_past 
        db.session.commit()
        self.assertEqual(user.current_streak, 5)
        self.assertEqual(user.last_cooked_date, date(2024, 5, 10))

class RecipeModelCase(BaseModelCase):
    def setUp(self):
        super().setUp()
        self.test_user = User(username='testuser', email='test@example.com')
        self.test_user.set_password('password')
        db.session.add(self.test_user)
        db.session.commit()

    def test_create_recipe(self):
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user, "Test user not found for recipe creation.")
        r = Recipe(name='Test Pancakes', category='Breakfast', time=30,
                   ingredients_json='["Flour", "Eggs", "Milk"]',
                   instructions='Mix and cook.', date='2024-05-10',
                   author=user, whitelist=[])
        db.session.add(r)
        db.session.commit()
        retrieved_recipe = Recipe.query.filter_by(name='Test Pancakes').first()
        self.assertIsNotNone(retrieved_recipe)
        self.assertEqual(retrieved_recipe.author.username, 'testuser')
        self.assertEqual(retrieved_recipe.ingredients, ["Flour", "Eggs", "Milk"])
        self.assertEqual(retrieved_recipe.whitelist, [])

    def test_recipe_ingredients_property(self):
        r = Recipe(name='Test Salad', category='Lunch', time=15,
                   ingredients_json='["Lettuce", "Tomato", "Cucumber"]',
                   instructions='Chop and mix.', date='2024-05-11',
                   user_id=self.test_user.id)
        self.assertEqual(r.ingredients, ["Lettuce", "Tomato", "Cucumber"])
        r.ingredients = "Carrot, Onion"
        self.assertEqual(r.ingredients, ["Carrot", "Onion"])
        self.assertEqual(r.ingredients_json, '["Carrot", "Onion"]')
        r.ingredients = ["Pepper", "Salt"]
        self.assertEqual(r.ingredients, ["Pepper", "Salt"])
        self.assertEqual(r.ingredients_json, '["Pepper", "Salt"]')

    def test_recipe_ingredients_setter_edge_cases(self):
        r = Recipe(name='Edge Case Ingredients', category='Test', time=5,
                   instructions='Test', date='2024-05-10', user_id=self.test_user.id)
        r.ingredients = ""
        self.assertEqual(r.ingredients, [])
        self.assertEqual(r.ingredients_json, '[]')
        r.ingredients = ",,"
        self.assertEqual(r.ingredients, [])
        self.assertEqual(r.ingredients_json, '[]')
        r.ingredients = "  item1  , ,, item2  , "
        self.assertEqual(r.ingredients, ["item1", "item2"])
        self.assertEqual(r.ingredients_json, '["item1", "item2"]')
        r.ingredients = ["", "item3", "  ", "item4", "item5 " ] 
        self.assertEqual(r.ingredients, ["item3", "item4", "item5"])
        self.assertEqual(r.ingredients_json, '["item3", "item4", "item5"]')
        r.ingredients = None
        self.assertEqual(r.ingredients, [])
        self.assertEqual(r.ingredients_json, '[]')

    def test_recipe_to_dict(self):
        r = Recipe(name='Dict Recipe', category='Test', time=10,
                   ingredients_json='["itemA"]', instructions='Test dict.',
                   date='2024-05-10', author=self.test_user, image="image_data.png")
        db.session.add(r)
        db.session.commit()
        recipe_dict = r.to_dict()
        self.assertEqual(recipe_dict['id'], r.id)
        self.assertEqual(recipe_dict['user_id'], self.test_user.id)

    def test_recipe_default_whitelist(self):
        r = Recipe(name='New Recipe', category='Dinner', time=60,
                   ingredients_json='[]', instructions='Cook.',
                   date='2024-05-13', user_id=self.test_user.id)
        db.session.add(r)
        db.session.commit()
        self.assertIsNotNone(r.whitelist)
        self.assertIsInstance(r.whitelist, list)
        self.assertEqual(r.whitelist, [])
    
    def test_recipe_whitelist(self):
        recipe = Recipe(name='Shared Stew', category='Dinner', time=90,
                        ingredients_json='["Meat", "Veggies"]', instructions='Simmer.',
                        date='2024-05-12', user_id=self.test_user.id, whitelist=[])
        db.session.add(recipe)
        db.session.commit()
        another_user_id = self.test_user.id + 1
        current_whitelist = list(recipe.whitelist) if recipe.whitelist is not None else []
        if another_user_id not in current_whitelist:
            current_whitelist.append(another_user_id)
            recipe.whitelist = current_whitelist
            db.session.commit()
        retrieved_recipe = db.session.get(Recipe, recipe.id) 
        self.assertIsNotNone(retrieved_recipe)
        self.assertIn(another_user_id, retrieved_recipe.whitelist)
        self.assertEqual(len(retrieved_recipe.whitelist), 1)

class CookingLogModelCase(BaseModelCase):
    def setUp(self):
        super().setUp()
        self.user1 = User(username='cook1', email='cook1@example.com')
        self.user1.set_password('pass1')
        self.recipe1 = Recipe(name='Omelette', category='Breakfast', time=10,
                              ingredients_json='["Eggs", "Cheese"]', instructions='Cook it.',
                              date='2024-01-01', author=self.user1)
        db.session.add_all([self.user1, self.recipe1])
        db.session.commit()

    def test_create_cooking_log(self):
        log_date = date(2024, 5, 10)
        log = CookingLog(user_id=self.user1.id, recipe_id=self.recipe1.id,
                         date_cooked=log_date, duration_seconds=1200, rating=5,
                         notes="Perfectly fluffy!")
        db.session.add(log)
        db.session.commit()
        retrieved_log = db.session.get(CookingLog, log.id)
        self.assertIsNotNone(retrieved_log)
        self.assertEqual(retrieved_log.cook.username, 'cook1')
        self.assertEqual(retrieved_log.recipe_logged.name, 'Omelette')
        self.assertEqual(retrieved_log.rating, 5)

    def test_cooking_log_defaults(self):
        log = CookingLog(user_id=self.user1.id, recipe_id=self.recipe1.id)
        db.session.add(log)
        db.session.commit() # Log is created, created_at is set

        # Retrieve the log again to get the value from the DB
        # This is important because the default lambda is executed on INSERT
        retrieved_log = db.session.get(CookingLog, log.id)
        self.assertIsNotNone(retrieved_log)
        self.assertIsNotNone(retrieved_log.created_at) # Ensure it's not None

        self.assertEqual(retrieved_log.date_cooked, date.today())
        
        # Make the retrieved_log.created_at timezone-aware, assuming it's UTC
        # If it's already aware from DB (depends on DB driver/SQLAlchemy config), this is safe.
        # If it's naive, this makes it aware.
        created_at_aware = retrieved_log.created_at.replace(tzinfo=timezone.utc)

        self.assertLess((datetime.now(timezone.utc) - created_at_aware), timedelta(seconds=5))
        self.assertIsNone(retrieved_log.duration_seconds)
        self.assertIsNone(retrieved_log.rating)
        self.assertIsNone(retrieved_log.notes)
        # print("test_cooking_log_defaults: PASSED")

    def test_cooking_log_optional_fields_none(self):
        log = CookingLog(user_id=self.user1.id, recipe_id=self.recipe1.id,
                         date_cooked=date(2024,5,1),
                         duration_seconds=None, rating=None, notes=None)
        db.session.add(log)
        db.session.commit()
        retrieved_log = db.session.get(CookingLog, log.id)
        self.assertIsNone(retrieved_log.duration_seconds)
        self.assertIsNone(retrieved_log.rating)
        self.assertIsNone(retrieved_log.notes)
    
    def test_user_streak_logic_first_log(self):
        user = db.session.get(User, self.user1.id)
        self.assertEqual(user.current_streak, 0)
        self.assertIsNone(user.last_cooked_date)
        log_date_1 = date(2024, 5, 1)
        if user.last_cooked_date is None or log_date_1 > user.last_cooked_date:
            user.last_cooked_date = log_date_1
        user.current_streak = 1
        db.session.commit()
        self.assertEqual(user.current_streak, 1)
        self.assertEqual(user.last_cooked_date, log_date_1)

    def test_user_streak_logic_consecutive_days(self):
        user = db.session.get(User, self.user1.id)
        log_date_1 = date(2024, 5, 1)
        user.last_cooked_date = log_date_1
        user.current_streak = 1
        db.session.commit()
        log_date_2 = date(2024, 5, 2)
        if user.last_cooked_date:
            days_diff = (log_date_2 - user.last_cooked_date).days
            if days_diff == 1: user.current_streak += 1
            elif days_diff > 1: user.current_streak = 1
        user.last_cooked_date = log_date_2
        db.session.commit()
        self.assertEqual(user.current_streak, 2)
        self.assertEqual(user.last_cooked_date, log_date_2)

    def test_user_streak_logic_gap_day(self):
        user = db.session.get(User, self.user1.id)
        log_date_1 = date(2024, 5, 1)
        user.last_cooked_date = log_date_1
        user.current_streak = 5
        db.session.commit()
        log_date_gap = date(2024, 5, 4)
        if user.last_cooked_date:
            days_diff = (log_date_gap - user.last_cooked_date).days
            if days_diff == 1: user.current_streak += 1
            elif days_diff > 1: user.current_streak = 1 
        user.last_cooked_date = log_date_gap
        db.session.commit()
        self.assertEqual(user.current_streak, 1)
        self.assertEqual(user.last_cooked_date, log_date_gap)

if __name__ == '__main__':
    unittest.main(verbosity=2)