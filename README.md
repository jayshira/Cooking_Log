# KitchenLog

**KitchenLog** is your personal digital cookbook and cooking diary that not only serves as a repository for your favorite recipes but also tracks your cooking sessions, offers data-driven insights, and makes it easy to share culinary inspiration with friends. Whether you’re a budding chef or a seasoned cook, KitchenLog helps you discover your cooking patterns, improve your skills, and celebrate your culinary achievements.

## Project Overview

KitchenLog is a web application built with Flask (Python) on the backend and standard HTML, CSS, and JavaScript (including Fetch API for dynamic updates) on the frontend. It uses SQLAlchemy for database interaction (SQLite), Flask-Migrate for schema migrations, and Flask-Login/Werkzeug/Flask-WTF for user authentication and security.

Users can:
- **Store and Manage Recipes:** Add new recipes, edit existing ones, and organize them using categories.
- **Log Cooking Sessions:** Record cooking instances, track duration with a timer, rate meals, and add notes.
- **Track Cooking Streaks:** Automatically monitors consecutive days cooked.
- **View Statistics:** Analyze cooking habits with log-based statistics and charts.
- **Share Recipes:** Whitelist other users to view specific recipes and allow them to clone recipes to their own kitchen.

The application follows a Multi-Page Application (MPA) architecture, where Flask renders distinct HTML pages, enhanced with client-side JavaScript for dynamic content loading and API interactions.

## Team Members

| UWA ID   | Name            | GitHub Username                                    
| :------- | :-------------- | :---------------------------------------------
| 23868133 | Alison Barboza  | [BlossomXD1](https://github.com/BlossomXD1)     
| 24078797 | Jason Yulfan    | [jayshira](https://github.com/jayshira)            
| 22965587 | Jiwon Song      | [jiwon-07](https://github.com/jiwon-07)         
| 23769653 | Hunter Wang     | [BiliBiliMay](https://github.com/BiliBiliMay)  

## Key Features

### Introductory View (/)
- Displays a welcome message and provides links/buttons for Login and Sign Up.

### User Authentication (/auth/*)
- Secure user signup and login using Flask-Login, Werkzeug (for password hashing), and Flask-WTF (for form validation and CSRF protection).

### My Kitchen View (/home)
- **Recipe Management:**
    - **Add & Edit Recipe:** A dedicated tab with a form to add new or edit existing recipes (name, category, time, ingredients, instructions, optional image). Uses Fetch API for submission.
    - **View Recipes:** Dynamically loaded list of the user's recipes with search functionality. Links to a dedicated view page for each recipe.
    - **Delete Recipe:** Functionality to delete recipes (protected by CSRF, prevents deletion if cooking logs exist).
- **Cooking Log & Streak:**
    - **Log Session:** "Cook" button on owned recipes links to a dedicated `/start_cooking/<id>` page.
    - **Session Page:** Displays recipe details, provides an interactive timer, and a form to log date cooked, rating, and notes.
    - **Recent Activity & Streak:** Displays recent logs and current cooking streak on the `/home` view.
- **Cooking Statistics:** Tab showing statistics derived from logged cooking sessions (total sessions, most frequent recipe, time logged, average rating) with Chart.js visualizations.
- **Share & Clone Recipes:**
    - **Whitelist Users:** Owners can share recipes by adding other users to a recipe's whitelist.
    - **View Shared Recipes:** Whitelisted users can view recipes shared with them.
    - **Clone to My Kitchen:** Whitelisted users can clone a shared recipe into their own collection, becoming the owner of the copy.

## Technologies Used

- **Backend:**
    - Python 3
    - Flask (including Blueprints)
    - SQLAlchemy (ORM)
    - Flask-Migrate (Database schema migrations)
    - Flask-Login (User session management)
    - Werkzeug (Password hashing, WSGI utilities)
    - Flask-WTF (Form handling, CSRF protection)
    - email-validator
- **Database:**
    - SQLite
- **Frontend:**
    - HTML, CSS, Vanilla JavaScript
    - Fetch API for AJAX calls
    - Chart.js for data visualizations

## Project File Structure

```text
KitchenLog/
├── app/ # Main application package
│ ├── init.py # Application factory (create_app) and extension initialization
│ ├── auth.py # Authentication blueprint (signup, login, logout routes)
│ ├── forms.py # WTForms definitions (SignupForm, LoginForm)
│ ├── models.py # SQLAlchemy database models (User, Recipe, CookingLog)
│ ├── routes.py # Main application blueprint (core routes and API endpoints)
│ ├── static/ # Static files
│ │ ├── style.css # Main stylesheet
│ │ └── script.js # Main JavaScript file (Fetch API, DOM manipulation, charts)
│ └── templates/ # Jinja2 HTML templates
│ ├── auth/ # Authentication-specific templates
│ │ ├── login.html
│ │ └── signup.html
│ ├── cooking_session.html
│ ├── home.html # Main user dashboard
│ ├── index.html # Public landing page
│ └── view_recipe.html # Detailed recipe view page
├── migrations/ # Flask-Migrate (Alembic) migration scripts
│ ├── versions/
│ └── ... (env.py, script.py.mako, etc.)
├── tests/ # Unit and integration tests
│ ├── init.py # Makes 'tests' a package (can be empty)
│ ├── test_models.py # Unit tests for database models
│ ├── test_forms.py # Unit tests for forms
│ └── test_routes.py # Integration tests for Flask routes/views
├── venv/ # Virtual environment (if named 'venv', usually in .gitignore)
├── config.py # Configuration classes (Config, DevelopmentConfig, TestConfig)
├── requirements.txt # Python package dependencies
├── run.py # Script to run the Flask development server
├── recipes.db # SQLite database file (for development, often in .gitignore or instance folder)
└── README.md # This file
```

## Prerequisites

- Python (version 3.9 or higher recommended, due to `zoneinfo`)
- `pip` (Python package installer)
- Git

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd KitchenLog 
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python3 -m venv venv  # Or python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate  # Windows
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Setup (Using Flask-Migrate):**
    The application uses Flask-Migrate to manage database schema changes.
    *   **For the very first time setting up the database:**
        ```bash
        flask db upgrade 
        ```
        This will create the `recipes.db` file (if it doesn't exist) and apply all existing migrations to create the tables according to your models.
    *   **If you pull changes that include new model definitions or modifications:**
        Always run `flask db upgrade` to apply any new migrations to your local database.
    *   **When making changes to `app/models.py`:**
        1.  `flask db migrate -m "A descriptive message about your model changes"`
        2.  Review the generated migration script in the `migrations/versions/` directory.
        3.  `flask db upgrade` (to apply the changes to your database).

## Running the Application

1.  **Ensure Virtual Environment is Active.**
2.  **Ensure Database is Up-to-Date:** (Run `flask db upgrade` if you pulled new changes).
3.  **Start the Flask Development Server:**
    From the project's root directory:
    ```bash
    python run.py
    ```
4.  **Access the Application:**
    Open your web browser and navigate to: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## Running Tests

The project uses Python's built-in `unittest` framework. Tests are located in the `tests/` directory.

1.  **Ensure Virtual Environment is Active.**
2.  **To run all tests:**
    From the project's root directory, execute:
    ```bash
    python -m unittest discover -s tests
    ```
    For more detailed output, add the `-v` (verbose) flag:
    ```bash
    python -m unittest discover -s tests -v
    ```

3.  **To run tests in a specific file (e.g., `test_models.py`):**
    ```bash
    python -m unittest tests.test_models
    ```

4.  **To run a specific test class within a file (e.g., `UserModelCase` in `test_models.py`):**
    ```bash
    python -m unittest tests.test_models.UserModelCase
    ```

5.  **To run a single specific test method (e.g., `test_password_hashing` in `UserModelCase`):**
    ```bash
    python -m unittest tests.test_models.UserModelCase.test_password_hashing
    ```
    Tests are configured to use an in-memory SQLite database (`TestConfig`) and do not affect your development database (`recipes.db`).

---
