import unittest
from threading import Thread

from config import TestConfig
from app import db, create_app
from app.models import User

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager

localhost = "http://127.0.0.1:5000/"

def setup_test_database():
    db.create_all()

    #User 1
    user1 = User(username="prebuilduser1", email="prebuilduser1@gmail.com")
    user1.set_password("prebuilduser1password")
    db.session.add(user1)

    #User 2
    user2 = User(username="prebuilduser2", email="prebuilduser2@gmail.com")
    user2.set_password("prebuilduser2password")
    db.session.add(user2)

    db.session.commit()

class SeleniumTest(unittest.TestCase):
    # User login gets repetitive, so we make a helper function for it
    def helper_login(self, username="prebuilduser1", password="prebuilduser1password"):
        self.driver.get(localhost + "auth/login")

        # Find the username and password fields
        username_field = self.driver.find_element(By.ID, "identifier")
        password_field = self.driver.find_element(By.ID, "password")

        # Fill in the fields
        username_field.send_keys(username)
        password_field.send_keys(password)

        # Submit the form
        submit_button = self.driver.find_element(By.ID, "submit")
        submit_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_changes(localhost + "auth/login")
        )

    def helper_logout(self):
        logout_button = self.driver.find_element(By.ID, "logout")
        logout_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_changes(localhost + "home")
        )

    def helper_add_recipe(self):
        add_recipe_button = self.driver.find_element(By.ID, "add-recipe-button")
        add_recipe_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element_attribute(
                (By.ID, "add"),
                "class",
                "active"
            )
        )

        # Find the recipe fields
        recipe_name_field = self.driver.find_element(By.ID, "recipe-name")
        recipe_time_field = self.driver.find_element(By.ID, "recipe-time")
        recipe_ingredients_field = self.driver.find_element(By.ID, "ingredient-input")
        recipe_add_button = self.driver.find_element(By.ID, "add-ingredient-btn")
        recipe_instructions_field = self.driver.find_element(By.ID, "recipe-instructions")

        # Fill in the fields
        recipe_name_field.send_keys("Test Recipe")
        recipe_time_field.send_keys("30")
        recipe_ingredients_field.send_keys("Test1 30g")
        recipe_add_button.click()
        recipe_ingredients_field.send_keys("Test2 20g")
        recipe_add_button.click()
        recipe_instructions_field.send_keys("Test instructions")

        # Special case for category
        recipe_category_field = Select(self.driver.find_element(By.ID, "recipe-category"))
        recipe_category_field.select_by_visible_text("Dessert")

        # Submit the form
        submit_button = self.driver.find_element(By.ID, "save-recipe-btn")
        submit_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element_attribute(
                (By.ID, "my-recipes-button"),
                "class",
                "active"
            )
        )
    def helper_share_recipe(self):
        # Find the share button for the first recipe
        share_button = self.driver.find_element(By.ID, "share-recipe-button")
        share_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element_attribute(
                (By.ID, "share"),
                "class",
                "active"
            )
        )

        recipe_select = Select(self.driver.find_element(By.ID, "share-recipe"))
        recipe_select.select_by_visible_text("Test Recipe")
        
        share_username_field = self.driver.find_element(By.ID, "user-search")
        share_username_field.send_keys("prebuilduser2")

        # Submit the form
        submit_button = self.driver.find_element(By.ID, "add-to-whitelist-btn")
        submit_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "response-message"),
                ("Recipe 'Test Recipe' shared with prebuilduser2.")
            )
        )

    def setUp(self):
        self.testApp = create_app(TestConfig)
        self.app_context = self.testApp.app_context()
        self.app_context.push()

        #db stuff and prebuilduser
        setup_test_database()

        self.server_thread = Thread(
            target=self.testApp.run,
            kwargs={'use_reloader': False}
        )
        self.server_thread.daemon = True
        self.server_thread.start()

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(
            #options=options
        )

        return super().setUp()
    
    def tearDown(self):
        self.driver.quit() 
        self.app_context.pop()

        return super().tearDown()

    # just see if the website even loads
    def test_indexpage_loads(self):
        self.driver.get(localhost)
        self.assertEqual("Welcome - KitchenLog", self.driver.title)
    
    # tests to see if user creation works
    def test_user_creation(self):
        self.driver.get(localhost + "auth/signup")

        # Find the username and password fields
        username_field = self.driver.find_element(By.ID, "username")
        email_field = self.driver.find_element(By.ID, "email")
        password_field = self.driver.find_element(By.ID, "password")
        confirm_password_field = self.driver.find_element(By.ID, "confirm_password")

        # Fill in the fields
        username_field.send_keys("testuser")
        email_field.send_keys("testuser@gmail.com")
        password_field.send_keys("testStrongPassword679!!")
        confirm_password_field.send_keys("testStrongPassword679!!")

        # Submit the form
        submit_button = self.driver.find_element(By.ID, "submit")
        submit_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_changes(self.driver.current_url)
        )

        # Check if the registration was successful
        success_message = self.driver.find_element(By.CLASS_NAME, "alert-success")
        self.assertEqual("Your account has been created! You can now log in.\n×", success_message.text)
    
    def test_user_login(self):
        self.helper_login()

        # Check if the login was successful
        welcome_message = self.driver.find_element(By.ID, "welcome-message")
        self.assertEqual("Welcome, prebuilduser1!", welcome_message.text)
    
    def test_user_logout(self):
        self.helper_login()
        self.helper_logout()
        

        logout_message = self.driver.find_element(By.CLASS_NAME, "alert-info")
        self.assertEqual("You have been logged out.\n×", logout_message.text)
    
    def test_add_recipe(self):
        self.helper_login()
        self.helper_add_recipe()

        # Check if the recipe was added successfully
        recipe_title_field = self.driver.find_element(By.CLASS_NAME, "recipe-title")
        self.assertEqual("Test Recipe", recipe_title_field.text)

    # MORE SELENIUM TESTS HERE
    def test_delete_recipe(self):
        self.helper_login()
        self.helper_add_recipe()

        # Find the delete button for the first recipe
        delete_button = self.driver.find_element(By.CLASS_NAME, "btn-danger")
        delete_button.click()

        # Confirm deletion
        WebDriverWait(self.driver, 10).until(
            expected_conditions.alert_is_present())

        alert = self.driver.switch_to.alert
        alert.accept()

        self.assertTrue(True)
    
    def test_edit_recipe(self):
        self.helper_login()
        self.helper_add_recipe()

        # Find the edit button for the first recipe
        edit_button = self.driver.find_element(By.ID, "edit-recipe-btn")
        edit_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element_attribute(
                (By.ID, "add"),
                "class",
                "active"
            )
        )

        # Find the recipe fields
        recipe_name_field = self.driver.find_element(By.ID, "recipe-name")
        recipe_time_field = self.driver.find_element(By.ID, "recipe-time")
        recipe_ingredients_field = self.driver.find_element(By.ID, "ingredient-input")
        recipe_add_button = self.driver.find_element(By.ID, "add-ingredient-btn")
        recipe_instructions_field = self.driver.find_element(By.ID, "recipe-instructions")

        # Fill in the fields
        recipe_name_field.clear()
        recipe_name_field.send_keys("Edited Recipe")
        recipe_time_field.clear()
        recipe_time_field.send_keys("45")
        recipe_ingredients_field.clear()
        recipe_ingredients_field.send_keys("Edited1 50g")
        recipe_add_button.click()
        recipe_ingredients_field.send_keys("Edited2 40g")
        recipe_add_button.click()
        recipe_instructions_field.clear()
        recipe_instructions_field.send_keys("Edited instructions")

        # Submit the form
        submit_button = self.driver.find_element(By.ID, "save-recipe-btn")
        submit_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element_attribute(
                (By.ID, "my-recipes-button"),
                "class",
                "active"
            )
        )

        # Check if the recipe was edited successfully
        recipe_title_field = self.driver.find_element(By.CLASS_NAME, "recipe-title")
        self.assertEqual("Edited Recipe", recipe_title_field.text)
    
    def test_share_recipe(self):
        self.helper_login()
        self.helper_add_recipe()
        self.helper_share_recipe()

        self.assertTrue(True)
    
    def test_shareddd_recipe(self):
        # User 1 Stuff
        self.helper_login()
        self.helper_add_recipe()
        self.helper_share_recipe()
        self.helper_logout()

        # User 2 Stuff
        self.helper_login("prebuilduser2", "prebuilduser2password")
        mailbox_button = self.driver.find_element(By.ID, "mailbox-icon")
        mailbox_button.click()
        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element_attribute(
                (By.ID, "mailbox-popup"),
                "style",
                "display: block;"
            )
        )

        shared_recipe_name = self.driver.find_element(By.CLASS_NAME, "shared-recipe-name")
        self.assertEqual("Test Recipe", shared_recipe_name.text)
    


# Instructions to run the tests:
# 1. Ensure your application is running locally (e.g., on http://localhost:5000).
# 2. Run the tests using the command:
#    python3 -m unittest discover -s tests
