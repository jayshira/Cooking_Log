# tests/test_forms.py
import unittest
from app import create_app, db
from app.models import User
from app.forms import SignupForm, LoginForm # Import your forms
from config import TestConfig

class FormTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create a user for testing uniqueness validators
        self.existing_user = User(username='existinguser', email='existing@example.com')
        self.existing_user.set_password('password')
        db.session.add(self.existing_user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_signup_form_valid_data(self):
        """Test SignupForm with valid data."""
        # WTForms need to be instantiated within a request context or with csrf_enabled=False
        # For unit tests, we often disable CSRF or mock it. TestConfig has WTF_CSRF_ENABLED = False
        with self.app.test_request_context(): # Provides context for form
            form = SignupForm(
                username='newuser',
                email='new@example.com',
                password='newpassword',
                confirm_password='newpassword'
            )
            self.assertTrue(form.validate())
            # print("test_signup_form_valid_data: PASSED")

    def test_signup_form_invalid_email(self):
        """Test SignupForm with an invalid email format."""
        with self.app.test_request_context():
            form = SignupForm(username='test', email='not-an-email', password='pw', confirm_password='pw')
            self.assertFalse(form.validate())
            self.assertIn('email', form.errors)
            self.assertIn('Invalid email address.', form.errors['email'])
            # print("test_signup_form_invalid_email: PASSED")

    def test_signup_form_password_mismatch(self):
        """Test SignupForm with mismatched passwords."""
        with self.app.test_request_context():
            form = SignupForm(username='test', email='test@example.com', password='pw1', confirm_password='pw2')
            self.assertFalse(form.validate())
            self.assertIn('confirm_password', form.errors)
            self.assertIn('Passwords must match', form.errors['confirm_password'])
            # print("test_signup_form_password_mismatch: PASSED")

    def test_signup_form_existing_username(self):
        """Test SignupForm custom validator for existing username."""
        with self.app.test_request_context():
            form = SignupForm(
                username='existinguser', # This username already exists
                email='another@example.com',
                password='password',
                confirm_password='password'
            )
            self.assertFalse(form.validate())
            self.assertIn('username', form.errors)
            self.assertIn('Username is already taken.', form.errors['username'])
            # print("test_signup_form_existing_username: PASSED")

    def test_signup_form_existing_email(self):
        """Test SignupForm custom validator for existing email."""
        with self.app.test_request_context():
            form = SignupForm(
                username='anotheruser',
                email='existing@example.com', # This email already exists
                password='password',
                confirm_password='password'
            )
            self.assertFalse(form.validate())
            self.assertIn('email', form.errors)
            self.assertIn('Email is already registered.', form.errors['email'])
            # print("test_signup_form_existing_email: PASSED")

    def test_login_form_valid_data(self):
        """Test LoginForm with valid data."""
        with self.app.test_request_context():
            form = LoginForm(identifier='existinguser', password='password')
            self.assertTrue(form.validate()) # Basic validation, not checking DB here
            # print("test_login_form_valid_data: PASSED")

    def test_login_form_missing_identifier(self):
        """Test LoginForm with missing identifier."""
        with self.app.test_request_context():
            form = LoginForm(password='password')
            self.assertFalse(form.validate())
            self.assertIn('identifier', form.errors)
            # print("test_login_form_missing_identifier: PASSED")

if __name__ == '__main__':
    unittest.main(verbosity=2)