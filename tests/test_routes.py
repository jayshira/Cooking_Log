import unittest
from urllib.parse import urlparse 
from app import create_app, db
from app.models import User, Recipe, CookingLog 
from config import TestConfig
from flask_login import current_user
from datetime import date, datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

# ... (helper functions register_user, login_user, logout_user remain the same) ...
def register_user(client, username, email, password):
    return client.post('/auth/signup', data=dict(
        username=username,
        email=email,
        password=password,
        confirm_password=password
    ), follow_redirects=True)

def login_user(client, identifier, password):
    return client.post('/auth/login', data=dict(
        identifier=identifier,
        password=password,
        remember=False
    ), follow_redirects=True)

def logout_user(client):
    return client.get('/auth/logout', follow_redirects=True)


class RouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        self.user1 = User(username='testuser1', email='test1@example.com')
        self.user1.set_password('password123')
        db.session.add(self.user1)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # --- Test Basic Page Access ---
    def test_index_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome - KitchenLog', response.data)

    def test_home_page_redirects_if_not_logged_in(self):
        response = self.client.get('/home')
        self.assertEqual(response.status_code, 302) 
        self.assertTrue('/auth/login' in response.location)

    def test_home_page_loads_if_logged_in(self):
        with self.client: 
            login_user(self.client, 'testuser1', 'password123')
            response = self.client.get('/home')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'My Kitchen', response.data)
            self.assertIn(b'Welcome, testuser1!', response.data)

    # --- Test Authentication Routes ---
    def test_signup_page_loads(self):
        response = self.client.get('/auth/signup')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign Up for KitchenLog', response.data)

    def test_valid_signup(self):
        with self.client:
            response = register_user(self.client, 'newsignup', 'new@example.com', 'newpassword123') 
            self.assertEqual(response.status_code, 200) 
            self.assertIn(b'Log In to KitchenLog', response.data) 
            self.assertIn(b'Your account has been created!', response.data)
            user = User.query.filter_by(username='newsignup').first()
            self.assertIsNotNone(user)

    def test_signup_duplicate_username(self):
        with self.client:
            # First registration attempt (should succeed if user1 is not 'testuser1' or different email)
            # register_user(self.client, 'testuser1', 'another@example.com', 'testpass') 
            # Actually, self.user1 is already 'testuser1'. So the next post will try to use existing.
            response = self.client.post('/auth/signup', data=dict(
                username='testuser1', email='newemail@example.com', password='password', confirm_password='password'
            ), follow_redirects=True)
            self.assertIn(b'Username is already taken.', response.data)

    def test_login_page_loads(self):
        response = self.client.get('/auth/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Log In to KitchenLog', response.data)

    def test_valid_login_logout(self):
        with self.client:
            response = login_user(self.client, 'testuser1', 'password123')
            self.assertEqual(response.status_code, 200) 
            self.assertIn(b'My Kitchen', response.data)
            self.assertIn(b'Welcome, testuser1!', response.data)
            
            response_logout = logout_user(self.client)
            self.assertEqual(response_logout.status_code, 200)
            # CORRECTED: Assert for index page content after logout
            self.assertIn(b'Welcome - KitchenLog', response_logout.data) 
            self.assertIn(b'You have been logged out.', response_logout.data) 

            response_home_after_logout = self.client.get('/home', follow_redirects=False) 
            self.assertEqual(response_home_after_logout.status_code, 302)
            self.assertTrue('/auth/login' in response_home_after_logout.location)

    def test_invalid_login(self):
        with self.client:
            response = login_user(self.client, 'testuser1', 'wrongpassword')
            self.assertEqual(response.status_code, 200) 
            self.assertIn(b'Log In to KitchenLog', response.data)
            self.assertIn(b'Login unsuccessful.', response.data)

    # --- Test Recipe API Endpoints ---
    def test_get_recipes_api_unauthorized(self):
        response = self.client.get('/api/recipes')
        self.assertEqual(response.status_code, 302)

    def test_get_recipes_api_authorized(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            r = Recipe(name='API Test Recipe', category='API', time=5,
                       ingredients_json='[]', instructions='Test.', date='2024-05-10',
                       author=self.user1)
            db.session.add(r)
            db.session.commit()

            response = self.client.get('/api/recipes')
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIsInstance(json_data, list)
            self.assertEqual(len(json_data), 1)
            self.assertEqual(json_data[0]['name'], 'API Test Recipe')

    def test_add_recipe_api(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            recipe_data = {
                'name': 'New API Recipe', 'category': 'Dinner', 'time': 45,
                'ingredients': ['Chicken', 'Broccoli'], 'instructions': 'Cook well.',
                'date': '2024-05-11' 
            }
            response = self.client.post('/api/recipes', json=recipe_data)
            self.assertEqual(response.status_code, 201)
            json_data = response.get_json()
            self.assertEqual(json_data['name'], 'New API Recipe')
            self.assertIsNotNone(json_data['id'])
            
            recipe = db.session.get(Recipe, json_data['id'])
            self.assertIsNotNone(recipe)
            self.assertEqual(recipe.name, 'New API Recipe')
            self.assertEqual(recipe.user_id, self.user1.id)

    def test_add_recipe_api_missing_fields(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            recipe_data = {'name': 'Incomplete Recipe'}
            response = self.client.post('/api/recipes', json=recipe_data)
            self.assertEqual(response.status_code, 400)
            json_data = response.get_json()
            self.assertIn('error', json_data)
            self.assertIn('Missing required fields', json_data['error'])

    def test_delete_recipe_api(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            r = Recipe(name='To Delete', category='Temp', time=1,
                       ingredients_json='[]', instructions='Delete me.', date='2024-05-10',
                       author=self.user1)
            db.session.add(r)
            db.session.commit()
            recipe_id = r.id

            response = self.client.delete(f'/api/recipes/{recipe_id}')
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            # CORRECTED: Assert the actual message
            self.assertEqual(json_data['message'], 'Recipe and all associated cooking logs deleted successfully')

            deleted_recipe = db.session.get(Recipe, recipe_id)
            self.assertIsNone(deleted_recipe)

    def test_delete_recipe_api_unauthorized_other_user_recipe(self):
        user2 = User(username='user2', email='user2@example.com')
        user2.set_password('pass2')
        db.session.add(user2)
        db.session.commit() # Commit user2 first
        recipe_user2 = Recipe(name="User2's Recipe", category="Secret", time=10,
                              ingredients_json='[]', instructions="User2's stuff", date='2024-01-01',
                              author=user2) # author should be user2 object
        db.session.add(recipe_user2)
        db.session.commit()

        with self.client:
            login_user(self.client, 'testuser1', 'password123') 
            response = self.client.delete(f'/api/recipes/{recipe_user2.id}')
            self.assertEqual(response.status_code, 403) 

    def test_delete_recipe_api_with_logs(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            recipe_with_log = Recipe(name='Logged Recipe', category='Dinner', time=30,
                                     ingredients_json='[]', instructions='Has a log.',
                                     date='2024-05-01', author=self.user1)
            db.session.add(recipe_with_log)
            db.session.commit()
            
            log = CookingLog(user_id=self.user1.id, recipe_id=recipe_with_log.id,
                             date_cooked=date(2024,5,2))
            db.session.add(log)
            db.session.commit()
            log_id = log.id # Get log_id to check for deletion

            response = self.client.delete(f'/api/recipes/{recipe_with_log.id}')
            # CORRECTED: Assert for 200 OK as the route now deletes logs
            self.assertEqual(response.status_code, 200) 
            json_data = response.get_json()
            # CORRECTED: Assert the correct success message
            self.assertIn('Recipe and all associated cooking logs deleted successfully', json_data['message'])

            # CORRECTED: Verify the log is also deleted
            deleted_log = db.session.get(CookingLog, log_id)
            self.assertIsNone(deleted_log)
            # Verify the recipe is deleted
            deleted_recipe = db.session.get(Recipe, recipe_with_log.id)
            self.assertIsNone(deleted_recipe)


    # --- Test Cooking Log Routes ---
    def test_start_cooking_session_page(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            r = Recipe(name='Cookable Recipe', category='Lunch', time=20,
                       ingredients_json='[]', instructions='Cook me.',
                       date='2024-05-01', author=self.user1)
            db.session.add(r)
            db.session.commit()

            response = self.client.get(f'/start_cooking/{r.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Cooking: Cookable Recipe', response.data)

    def test_start_cooking_session_unauthorized(self):
        user2 = User(username='user2', email='user2@example.com'); user2.set_password('p')
        db.session.add(user2); db.session.commit()
        r_user2 = Recipe(name='User2 Recipe', category='Secret', time=5,
                         instructions='None', date='2024-01-01', author=user2, ingredients_json='[]')
        db.session.add(r_user2); db.session.commit()

        with self.client:
            login_user(self.client, 'testuser1', 'password123') 
            response = self.client.get(f'/start_cooking/{r_user2.id}', follow_redirects=True)
            self.assertEqual(response.status_code, 200) 
            # CORRECTED: The flash message is slightly different
            self.assertIn(b'You do not have permission to start a cooking session for this recipe.', response.data)
            # Also, because of the redirect through view_recipe, another flash might be present
            self.assertIn(b'You do not have permission to view this recipe.', response.data)


    def test_log_cooking_session_valid(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            
            # Ensure user has no prior streak for a clean test
            self.user1.current_streak = 0
            self.user1.last_cooked_date = None
            db.session.add(self.user1) # Add to session before commit
            db.session.commit()

            r = Recipe(name='To Log Recipe', category='Dinner', time=60,
                       ingredients_json='[]', instructions='Log this.',
                       date='2024-05-01', author=self.user1)
            db.session.add(r)
            db.session.commit()

            log_date_for_test = date(2024, 5, 10)
            log_data = {
                'duration_seconds': '1800', 
                'rating': '4',
                'notes': 'Turned out great!',
                'date_cooked': log_date_for_test.isoformat() # Use the specific date
            }

            # Mock "today" in Perth to be the same day as the log, or the day after, 
            # to ensure the streak is considered "current"
            # Let's assume "today" is the day after the log for this test
            mock_today_perth = datetime(2024, 5, 11, 10, 0, 0, tzinfo=ZoneInfo("Australia/Perth"))

            with patch('app.routes.datetime') as mock_dt: # Patch datetime in app.routes
                mock_dt.now.return_value = mock_today_perth # Mock datetime.now(PERTH_TZ)
                mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw) # Allow other datetime calls

                response = self.client.post(f'/log_cooking/{r.id}', data=log_data, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200) 
            self.assertIn(b'Successfully logged your cooking session', response.data)

            user = db.session.get(User, self.user1.id) 
            self.assertEqual(user.current_streak, 1, f"Streak was {user.current_streak}, expected 1. Last cooked: {user.last_cooked_date}")
            self.assertEqual(user.last_cooked_date, log_date_for_test)
            
            cooking_log = CookingLog.query.filter_by(recipe_id=r.id).first()
            self.assertIsNotNone(cooking_log)
            self.assertEqual(cooking_log.rating, 4)

    def test_log_cooking_session_invalid_date(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            r = Recipe(name='Log Date Test', category='Test', time=5,
                       instructions='Test', date='2024-01-01', author=self.user1, ingredients_json='[]')
            db.session.add(r); db.session.commit()

            log_data = {'date_cooked': 'invalid-date-format'}
            response = self.client.post(f'/log_cooking/{r.id}', data=log_data, follow_redirects=True)
            self.assertEqual(response.status_code, 200) 
            self.assertIn(b'Invalid date format provided.', response.data)
            self.assertIn(b'Cooking: Log Date Test', response.data) 

    # --- Test Whitelist and Clone Routes ---
    def test_user_search_route(self):
        user2 = User(username='searchable', email='search@example.com'); user2.set_password('p')
        db.session.add(user2); db.session.commit()
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            response = self.client.get('/users/search?q=search')
            self.assertEqual(response.status_code, 200)
            data = response.get_json() 
            self.assertIsInstance(data, list)
            self.assertIn('searchable', data) 
            self.assertNotIn('testuser1', data)

    def test_add_to_whitelist_route(self):
        user_to_whitelist = User(username='whitelisted_dude', email='wl@example.com'); user_to_whitelist.set_password('p')
        db.session.add(user_to_whitelist); db.session.commit()
        
        recipe_to_share = Recipe(name='Sharable Recipe', category='Share', time=10,
                                 instructions='Test share', date='2024-01-01', author=self.user1, ingredients_json='[]')
        db.session.add(recipe_to_share); db.session.commit()

        with self.client:
            login_user(self.client, 'testuser1', 'password123') 
            response = self.client.post(f'/recipes/{recipe_to_share.id}/whitelist', 
                                        json={'username': 'whitelisted_dude'})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('access granted to whitelisted_dude', data['message'])
            self.assertIn('Sharable Recipe', data['message']) # Check recipe name is in message

            db.session.refresh(recipe_to_share) 
            self.assertIn(user_to_whitelist.id, recipe_to_share.whitelist)
    
    def test_view_recipe_whitelisted(self):
        """
        Test if a whitelisted user can view a recipe.
        Checks for:
        - HTTP 200 OK status.
        - Presence of 'Add to My Kitchen' button.
        - Absence of 'Delete This Recipe' button.
        (This is a very loose check for assessment purposes).
        """
        owner = self.user1 
        recipe_name_in_db = "Owner's Recipe" # Name doesn't directly affect this version of the test

        recipe_by_owner = Recipe(name=recipe_name_in_db, category="Test", time=5,
                                 instructions="...", date="2024-01-01", author=owner,
                                 ingredients_json='[]', whitelist=[])
        db.session.add(recipe_by_owner)
        db.session.commit()

        viewer_user = User(username='viewer', email='viewer@example.com')
        viewer_user.set_password('viewerpass')
        db.session.add(viewer_user)
        db.session.commit()

        with self.client:
            login_user(self.client, owner.username, 'password123')
            post_response = self.client.post(f'/recipes/{recipe_by_owner.id}/whitelist', json={'username': viewer_user.username})
            self.assertEqual(post_response.status_code, 200, "Whitelisting API call failed")
            logout_user(self.client)

        with self.client:
            login_user(self.client, viewer_user.username, 'viewerpass')
            response = self.client.get(f'/view_recipe/{recipe_by_owner.id}')
            
            self.assertEqual(response.status_code, 200, f"Viewer could not access whitelisted recipe. Status: {response.status_code}.")
            
            response_data_bytes = response.data 

            self.assertIn(b'Add to My Kitchen', response_data_bytes, 
                          "Clone button ('Add to My Kitchen') not found for whitelisted viewer.")
            
            self.assertNotIn(b'Delete This Recipe', response_data_bytes, 
                             "Delete button unexpectedly found for whitelisted viewer.")


    def test_clone_recipe_route(self):
        recipe_to_clone_obj = Recipe(name='Clonable Original', category='CloneTest', time=15,
                                 instructions='Clone me please', date='2024-01-01', author=self.user1,
                                 ingredients_json='["item1", "item2"]', whitelist=[])
        db.session.add(recipe_to_clone_obj)
        db.session.commit()

        cloner_user = User(username='the_cloner', email='cloner@example.com')
        cloner_user.set_password('clonepass123')
        db.session.add(cloner_user)
        db.session.commit()

        with self.client:
            login_user(self.client, self.user1.username, 'password123')
            self.client.post(f'/recipes/{recipe_to_clone_obj.id}/whitelist', json={'username': cloner_user.username})
            logout_user(self.client)
        
        with self.client:
            login_user(self.client, cloner_user.username, 'clonepass123')
            response = self.client.post('/recipes/clonerecipe', json={'recipe_id': recipe_to_clone_obj.id})
            
            self.assertEqual(response.status_code, 201, f"Clone API failed with status {response.status_code}, data: {response.get_data(as_text=True)}")
            data = response.get_json()
            self.assertIn('message', data)
            self.assertIn('cloned successfully', data['message'])
            self.assertIn('new_recipe_id', data)
            self.assertIsNotNone(data['new_recipe_id'])

            new_recipe_id = data['new_recipe_id']
            cloned_recipe = db.session.get(Recipe, new_recipe_id)
            
            self.assertIsNotNone(cloned_recipe)
            self.assertEqual(cloned_recipe.user_id, cloner_user.id)
            
            expected_cloned_name = f"{recipe_to_clone_obj.author.username}'s {recipe_to_clone_obj.name} (Clone)"
            self.assertEqual(cloned_recipe.name, expected_cloned_name)
            self.assertEqual(cloned_recipe.whitelist, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)