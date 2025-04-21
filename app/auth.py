# app/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, db # Import User model and db instance from the app package
from . import bcrypt        # Import bcrypt instance from the app package
from .forms import SignupForm, LoginForm # Using WTForms now :D

# Create a Blueprint named 'auth'.
# The url_prefix='/auth' was added during registration in __init__.py,
# so all routes defined here will be prefixed with /auth.
auth = Blueprint('auth', __name__)


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration.', 'danger')
    
    return render_template('auth/signup.html', title='Sign Up', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Find user by either username or email
        user = User.query.filter((User.username == form.identifier.data) | 
                                 (User.email == form.identifier.data)).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
        else:
            flash('Login unsuccessful. Please check your credentials.', 'danger')
    
    return render_template('auth/login.html', title='Log In', form=form)


@auth.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index')) #mainpage