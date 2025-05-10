# tests/test_routes.py
import unittest
from urllib.parse import urlparse # For checking redirect locations
from app import create_app, db
from app.models import User, Recipe, CookingLog # Import your models
from config import TestConfig
from flask_login import current_user
from datetime import date, datetime, timedelta, timezone

# Helper function to register a user for tests
def register_user(client, username, email, password):
    return client.post('/auth/signup', data=dict(
        username=username,
        email=email,
        password=password,
        confirm_password=password
    ), follow_redirects=True)

# Helper function to log in a user
def login_user(client, identifier, password):
    return client.post('/auth/login', data=dict(
        identifier=identifier,
        password=password,
        remember=False # Or True, depending on what you want to test
    ), follow_redirects=True)

# Helper function to log out
def logout_user(client):
    return client.get('/auth/logout', follow_redirects=True)


class RouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client() # Create a test client

        # Optional: Create a default user for tests that require a logged-in user
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
        """Test that the index page loads correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome - KitchenLog', response.data) # Check for title or key content

    def test_home_page_redirects_if_not_logged_in(self):
        """Test that /home redirects to login if not authenticated."""
        response = self.client.get('/home')
        self.assertEqual(response.status_code, 302) # 302 is redirect
        self.assertTrue('/auth/login' in response.location)

    def test_home_page_loads_if_logged_in(self):
        """Test that /home loads if authenticated."""
        with self.client: # Use context manager to handle session
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
        """Test user registration with valid data."""
        with self.client:
            # Use a password that meets length criteria (min 8 chars)
            response = register_user(self.client, 'newsignup', 'new@example.com', 'newpassword123') 
            self.assertEqual(response.status_code, 200) 
            self.assertIn(b'Log In to KitchenLog', response.data) 
            self.assertIn(b'Your account has been created!', response.data)
            user = User.query.filter_by(username='newsignup').first()
            self.assertIsNotNone(user)

    def test_signup_duplicate_username(self):
        with self.client:
            register_user(self.client, 'testuser1', 'another@example.com', 'testpass') # Username exists
            response = self.client.post('/auth/signup', data=dict(
                username='testuser1', email='newemail@example.com', password='password', confirm_password='password'
            ), follow_redirects=True)
            self.assertIn(b'Username is already taken.', response.data)

    def test_login_page_loads(self):
        response = self.client.get('/auth/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Log In to KitchenLog', response.data)

    def test_valid_login_logout(self):
        """Test login with valid credentials and subsequent logout."""
        with self.client:
            # Login
            response = login_user(self.client, 'testuser1', 'password123')
            self.assertEqual(response.status_code, 200) # After redirect to home
            self.assertIn(b'My Kitchen', response.data)
            self.assertIn(b'Welcome, testuser1!', response.data)

            # Check current_user is set (can't directly check session variable easily without more setup)
            # Instead, access a protected route again or check for content specific to logged-in user
            response_home_again = self.client.get('/home')
            self.assertIn(b'Welcome, testuser1!', response_home_again.data)
            
            # Logout
            response_logout = logout_user(self.client)
            self.assertEqual(response_logout.status_code, 200) # After redirect to index
            self.assertIn(b'Welcome - KitchenLog', response_logout.data) # Should be on index page
            self.assertIn(b'You have been logged out.', response_logout.data) # Flash message

            # Accessing /home again should redirect to login
            response_home_after_logout = self.client.get('/home', follow_redirects=False) # Don't follow to see 302
            self.assertEqual(response_home_after_logout.status_code, 302)
            self.assertTrue('/auth/login' in response_home_after_logout.location)

    def test_invalid_login(self):
        with self.client:
            response = login_user(self.client, 'testuser1', 'wrongpassword')
            self.assertEqual(response.status_code, 200) # Stays on login page
            self.assertIn(b'Log In to KitchenLog', response.data)
            self.assertIn(b'Login unsuccessful.', response.data) # Flash message

    # --- Test Recipe API Endpoints (Basic) ---
    def test_get_recipes_api_unauthorized(self):
        response = self.client.get('/api/recipes')
        self.assertEqual(response.status_code, 302) # Redirects to login

    def test_get_recipes_api_authorized(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            # Create a recipe for this user
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
                'date': '2024-05-11' # Optional, backend might default
            }
            response = self.client.post('/api/recipes', json=recipe_data)
            self.assertEqual(response.status_code, 201) # 201 Created
            json_data = response.get_json()
            self.assertEqual(json_data['name'], 'New API Recipe')
            self.assertIsNotNone(json_data['id'])
            
            # Verify it's in the database
            recipe = db.session.get(Recipe, json_data['id'])
            self.assertIsNotNone(recipe)
            self.assertEqual(recipe.name, 'New API Recipe')
            self.assertEqual(recipe.user_id, self.user1.id)

    def test_add_recipe_api_missing_fields(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            recipe_data = {'name': 'Incomplete Recipe'} # Missing category, time, etc.
            response = self.client.post('/api/recipes', json=recipe_data)
            self.assertEqual(response.status_code, 400) # Bad Request
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
            self.assertEqual(json_data['message'], 'Recipe deleted successfully')

            # Verify it's deleted from DB
            deleted_recipe = db.session.get(Recipe, recipe_id)
            self.assertIsNone(deleted_recipe)

    def test_delete_recipe_api_unauthorized_other_user_recipe(self):
        # Create another user and their recipe
        user2 = User(username='user2', email='user2@example.com')
        user2.set_password('pass2')
        db.session.add(user2)
        db.session.commit()
        recipe_user2 = Recipe(name="User2's Recipe", category="Secret", time=10,
                              ingredients_json='[]', instructions="User2's stuff", date='2024-01-01',
                              author=user2)
        db.session.add(recipe_user2)
        db.session.commit()

        with self.client:
            login_user(self.client, 'testuser1', 'password123') # Log in as user1
            response = self.client.delete(f'/api/recipes/{recipe_user2.id}')
            self.assertEqual(response.status_code, 403) # Forbidden

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

            response = self.client.delete(f'/api/recipes/{recipe_with_log.id}')
            self.assertEqual(response.status_code, 409) # Conflict
            json_data = response.get_json()
            self.assertIn('Cannot delete recipe with existing cooking logs', json_data['error'])

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
        db.session.add(user2)
        r_user2 = Recipe(name='User2 Recipe', category='Secret', time=5,
                         instructions='None', date='2024-01-01', author=user2, ingredients_json='[]')
        db.session.add_all([user2, r_user2]); db.session.commit()

        with self.client:
            login_user(self.client, 'testuser1', 'password123') # Logged in as user1
            response = self.client.get(f'/start_cooking/{r_user2.id}', follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Redirects to home
            self.assertIn(b'You can only start cooking sessions for your own recipes.', response.data)

    def test_log_cooking_session_valid(self):
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            r = Recipe(name='To Log Recipe', category='Dinner', time=60,
                       ingredients_json='[]', instructions='Log this.',
                       date='2024-05-01', author=self.user1)
            db.session.add(r)
            db.session.commit()

            log_data = {
                'duration_seconds': '1800', # 30 minutes
                'rating': '4',
                'notes': 'Turned out great!',
                'date_cooked': '2024-05-10'
            }
            # Remember TestConfig has WTF_CSRF_ENABLED = False, so we don't need to send csrf_token here
            response = self.client.post(f'/log_cooking/{r.id}', data=log_data, follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Redirects to home
            self.assertIn(b'Successfully logged your cooking session', response.data)

            # Verify log created and streak updated
            user = db.session.get(User, self.user1.id)
            self.assertEqual(user.current_streak, 1) # Assuming this is the first log for streak
            self.assertEqual(user.last_cooked_date, date(2024, 5, 10))
            
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
            self.assertEqual(response.status_code, 200) # Redirects back to start_cooking page
            self.assertIn(b'Invalid date format provided.', response.data)
            self.assertIn(b'Cooking: Log Date Test', response.data) # Check we are on the right page

    # --- Test Whitelist and Clone Routes ---
    def test_user_search_route(self):
        user2 = User(username='searchable', email='search@example.com'); user2.set_password('p')
        db.session.add(user2); db.session.commit()
        with self.client:
            login_user(self.client, 'testuser1', 'password123')
            response = self.client.get('/users/search?q=search')
            self.assertEqual(response.status_code, 200)
            data = response.get_json() # This will be ['searchable'] or similar
            self.assertIsInstance(data, list)
            self.assertIn('searchable', data) # Check if the string 'searchable' is in the list
            self.assertNotIn('testuser1', data)

    def test_add_to_whitelist_route(self):
        user_to_whitelist = User(username='whitelisted_dude', email='wl@example.com'); user_to_whitelist.set_password('p')
        db.session.add(user_to_whitelist); db.session.commit()
        
        recipe_to_share = Recipe(name='Sharable Recipe', category='Share', time=10,
                                 instructions='Test share', date='2024-01-01', author=self.user1, ingredients_json='[]')
        db.session.add(recipe_to_share); db.session.commit()

        with self.client:
            login_user(self.client, 'testuser1', 'password123') # Logged in as owner
            response = self.client.post(f'/recipes/{recipe_to_share.id}/whitelist', 
                                        json={'username': 'whitelisted_dude'})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('shared with whitelisted_dude', data['message'])

            # Verify DB
            db.session.refresh(recipe_to_share) # Get fresh data from DB
            self.assertIn(user_to_whitelist.id, recipe_to_share.whitelist)

# tests/test_routes.py
    def test_view_recipe_whitelisted(self):
        """Test if a whitelisted user can view a recipe and sees the clone button."""
        owner = self.user1 
        recipe_name_with_apostrophe = "Owner's Recipe"
        
        # THIS IS THE CRITICAL LINE - It must be the HTML escaped version
        expected_html_substring = "Owner&#39;s Recipe"

        recipe_by_owner = Recipe(name=recipe_name_with_apostrophe, category="Test", time=5,
                                 instructions="...", date="2024-01-01", author=owner,
                                 ingredients_json='[]', whitelist=[])
        db.session.add(recipe_by_owner)
        db.session.commit()

        viewer_user = User(username='viewer', email='viewer@example.com')
        viewer_user.set_password('viewerpass')
        db.session.add(viewer_user)
        db.session.commit()

        # Owner (testuser1) whitelists viewer_user
        with self.client:
            login_user(self.client, owner.username, 'password123')
            post_response = self.client.post(f'/recipes/{recipe_by_owner.id}/whitelist', json={'username': viewer_user.username})
            self.assertEqual(post_response.status_code, 200, "Whitelisting API call failed")
            logout_user(self.client)

        # Viewer (viewer_user) logs in and tries to view
        with self.client:
            login_user(self.client, viewer_user.username, 'viewerpass')
            response = self.client.get(f'/view_recipe/{recipe_by_owner.id}')
            self.assertEqual(response.status_code, 200, f"Viewer could not access whitelisted recipe. Status: {response.status_code}. Data: {response.get_data(as_text=True)}")
            
            response_data_bytes = response.data 
            expected_bytes_to_find = expected_html_substring.encode('utf-8')

            # Debug prints from before (they are helpful)
            # print(f"\n--- DEBUG: test_view_recipe_whitelisted ---")
            # print(f"Expected substring (bytes to find): {repr(expected_bytes_to_find)}")
            # response_data_str_for_debug = response_data_bytes.decode('utf-8', errors='replace')
            # h1_start_index = response_data_str_for_debug.find("<h1>")
            # if h1_start_index != -1:
            #     h1_end_index = response_data_str_for_debug.find("</h1>", h1_start_index)
            #     if h1_end_index != -1:
            #         actual_h1_content = response_data_str_for_debug[h1_start_index : h1_end_index + 5]
            #         print(f"Actual H1 content from response (string): '{actual_h1_content}'")
            # else:
            #     print("H1 tag was not found in the response!")

            self.assertIn(expected_bytes_to_find, response_data_bytes, 
                          f"Expected byte sequence '{expected_bytes_to_find!r}' (which is '{expected_html_substring}') not found in response.")
            
            self.assertNotIn(b'Delete This Recipe', response_data_bytes, "Delete button unexpectedly found for whitelisted viewer.")
            self.assertIn(b'Add to My Kitchen', response_data_bytes, "Clone button ('Add to My Kitchen') not found for whitelisted viewer.")

def test_clone_recipe_route(self):
        # This is the recipe that will be cloned
        recipe_to_clone_obj = Recipe(name='Clonable Original', category='CloneTest', time=15,
                                 instructions='Clone me please', date='2024-01-01', author=self.user1,
                                 ingredients_json='["item1", "item2"]', whitelist=[])
        db.session.add(recipe_to_clone_obj)
        db.session.commit()

        # User who will perform the cloning action
        cloner_user = User(username='the_cloner', email='cloner@example.com')
        cloner_user.set_password('clonepass123')
        db.session.add(cloner_user)
        db.session.commit()

        # Owner (self.user1) whitelists cloner_user for recipe_to_clone_obj
        with self.client:
            login_user(self.client, self.user1.username, 'password123')
            self.client.post(f'/recipes/{recipe_to_clone_obj.id}/whitelist', json={'username': cloner_user.username})
            logout_user(self.client)
        
        # Now, cloner_user logs in and clones the recipe
        with self.client:
            login_user(self.client, cloner_user.username, 'clonepass123')
            # Make the POST request to clone
            response = self.client.post('/recipes/clonerecipe', json={'recipe_id': recipe_to_clone_obj.id})
            
            self.assertEqual(response.status_code, 201, f"Clone API failed with status {response.status_code}, data: {response.get_data(as_text=True)}")
            data = response.get_json()
            self.assertIn('message', data, "Response JSON missing 'message' key")
            self.assertIn('cloned successfully', data['message'])
            self.assertIn('new_recipe_id', data, "Response JSON missing 'new_recipe_id' key")
            self.assertIsNotNone(data['new_recipe_id'])

            new_recipe_id = data['new_recipe_id']
            cloned_recipe = db.session.get(Recipe, new_recipe_id) # Fetch the newly created recipe
            
            self.assertIsNotNone(cloned_recipe, f"Cloned recipe with ID {new_recipe_id} not found in DB.")
            self.assertEqual(cloned_recipe.user_id, cloner_user.id, "Cloned recipe not owned by cloner.")
            
            # Debug prints for the name check
            expected_suffix = ' (Clone)'
            # The name is constructed in the route as: f"{original_recipe.author.username}'s {original_recipe.name} (Clone)"
            # So, `original_recipe` here refers to `recipe_to_clone_obj`
            expected_base_name_part = f"{recipe_to_clone_obj.author.username}'s {recipe_to_clone_obj.name}"
            
            print(f"\nDEBUG (test_clone_recipe_route):")
            print(f"  Original Recipe Name for Cloning: '{recipe_to_clone_obj.name}'")
            print(f"  Original Recipe Author: '{recipe_to_clone_obj.author.username}'")
            print(f"  Actual Cloned Recipe Name from DB: '{cloned_recipe.name}'")
            print(f"  Expected base part of cloned name: '{expected_base_name_part}'")
            print(f"  Expected suffix for cloned name: '{expected_suffix}'")

            # Make the assertion more specific if the f-string construction is complex
            # self.assertTrue(cloned_recipe.name.startswith(expected_base_name_part), 
            #                 f"Cloned name '{cloned_recipe.name}' does not start with '{expected_base_name_part}'")
            self.assertTrue(cloned_recipe.name.endswith(expected_suffix), 
                            f"Cloned name '{cloned_recipe.name}' does not end with '{expected_suffix}'")
            self.assertEqual(cloned_recipe.name, f"{expected_base_name_part}{expected_suffix}",
                             "Full cloned name does not match expected construction.")

            self.assertEqual(cloned_recipe.whitelist, [], "Cloned recipe whitelist should be empty.")

if __name__ == '__main__':
    unittest.main(verbosity=2)