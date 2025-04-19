# app/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, db # Import User model and db instance
from . import bcrypt        # Import bcrypt instance

auth = Blueprint('auth', __name__)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user signup."""
    if current_user.is_authenticated:
        return redirect(url_for('main.home')) # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Basic validation (add more robust validation later)
        if not username or not email or not password or not confirm_password:
            flash('Please fill in all fields.', 'warning')
            return redirect(url_for('auth.signup'))

        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return redirect(url_for('auth.signup'))

        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists. Please choose different ones or login.', 'warning')
            return redirect(url_for('auth.signup'))

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password) # Hash password

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during signup. Please try again.', 'danger')
            print(f"Signup Error: {e}") # Log error
            return redirect(url_for('auth.signup'))

    # For GET request, render the signup form
    return render_template('auth/signup.html', title='Sign Up')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.home')) # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username') # Can use username or email to login
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash('Please enter username/email and password.', 'warning')
            return redirect(url_for('auth.login'))

        # Find user by username or email
        user = User.query.filter((User.username == username) | (User.email == username)).first()

        # Check if user exists and password is correct
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')
            # Redirect to the page they were trying to access, or main index
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check username/email and password.', 'danger')
            return redirect(url_for('auth.login'))

    # For GET request, render the login form
    return render_template('auth/login.html', title='Log In')

@auth.route('/logout')
@login_required # User must be logged in to log out
def logout():
    """Handles user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login')) # Redirect to home page