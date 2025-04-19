# app/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, db # Import User model and db instance from the app package
from . import bcrypt        # Import bcrypt instance from the app package

# Create a Blueprint named 'auth'.
# The url_prefix='/auth' was added during registration in __init__.py,
# so all routes defined here will be prefixed with /auth.
auth = Blueprint('auth', __name__)


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user registration."""
    # If the user is already logged in, redirect them to the main application page.
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    # Handle the POST request when the form is submitted
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # --- Basic Input Validation ---
        # Check if any fields are empty
        if not username or not email or not password or not confirm_password:
            flash('Please fill in all fields.', 'warning')
            # Re-render form, passing back entered data for better UX
            return render_template('auth/signup.html', title='Sign Up',
                                   username=username, email=email)

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            # Re-render form, passing back entered data
            return render_template('auth/signup.html', title='Sign Up',
                                   username=username, email=email)

        # --- Add more robust validation here if needed ---
        # (e.g., check email format, password complexity, username length/chars)

        # --- Check for Existing User ---
        # Query the database to see if a user with this username OR email already exists.
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            # Provide specific feedback about which field is taken
            if existing_user.username == username:
                flash('Username already exists. Please choose a different one.', 'warning')
            else: # Must be the email
                flash('Email address already registered. Please log in or use a different email.', 'warning')
            # Re-render form with entered data
            return render_template('auth/signup.html', title='Sign Up',
                                   username=username, email=email)

        # --- Create New User ---
        # If validation passes and user doesn't exist, create a new User instance
        new_user = User(username=username, email=email)
        # Hash the password using the method defined in the User model
        new_user.set_password(password)

        # --- Add to Database ---
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            # Redirect to the login page after successful signup
            return redirect(url_for('auth.login'))
        except Exception as e:
            # If a database error occurs, rollback the transaction
            db.session.rollback()
            flash('An error occurred during signup. Please try again later.', 'danger')
            print(f"Signup Database Error: {e}") # Log the error for debugging
            # Show signup page again on error
            return render_template('auth/signup.html', title='Sign Up',
                                   username=username, email=email)

    # Handle the GET request (user navigates to /auth/signup)
    # Just render the signup form template.
    return render_template('auth/signup.html', title='Sign Up')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    # If the user is already logged in, redirect them to the main application page.
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    # Handle the POST request when the login form is submitted
    if request.method == 'POST':
        # The 'username' form field can accept either a username or an email
        identifier = request.form.get('username')
        password = request.form.get('password')
        # Check if the 'Remember Me' checkbox was ticked
        remember = True if request.form.get('remember') else False

        # --- Basic Input Validation ---
        if not identifier or not password:
            flash('Please enter username/email and password.', 'warning')
            # Re-render form, passing back identifier for better UX
            return render_template('auth/login.html', title='Log In', identifier=identifier)

        # --- Find User ---
        # Attempt to find the user by either username or email in the database.
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

        # --- Validate Password and Log In ---
        # Check if a user was found AND if the provided password is correct (using the model's method)
        if user and user.check_password(password):
            # Log the user in using Flask-Login's function.
            # This handles setting the session cookie.
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')

            # --- Redirect After Login ---
            # Check if the user was trying to access a protected page ('next' query parameter)
            next_page = request.args.get('next')
            # Basic security: Ensure 'next' URL is relative (starts with '/') to prevent open redirect attacks.
            if next_page and not next_page.startswith('/'):
                 next_page = None # Discard potentially unsafe external URLs

            # Redirect to the intended page or the main 'home' page if 'next' is not set or unsafe.
            return redirect(next_page or url_for('main.home'))
        else:
            # If user not found or password incorrect, show an error message.
            flash('Login Unsuccessful. Please check username/email and password.', 'danger')
            # Re-render the login page with the error message.
            return render_template('auth/login.html', title='Log In', identifier=identifier)

    # Handle the GET request (user navigates to /auth/login)
    # Just render the login form template.
    return render_template('auth/login.html', title='Log In')


@auth.route('/logout')
@login_required # Ensures only logged-in users can access this route
def logout():
    """Handles user logout."""
    # Log the user out using Flask-Login's function.
    # This removes the user ID from the session.
    logout_user()
    flash('You have been logged out successfully.', 'info')
    # Redirect the user to the public landing page after logout.
    return redirect(url_for('main.index'))