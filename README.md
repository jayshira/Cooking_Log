Okay, let's integrate the required information into your existing README.md. I'll add the team table and the placeholder for test instructions.

# KitchenLog

**KitchenLog** is your personal digital cookbook and cooking diary that not only serves as a repository for your favorite recipes but also tracks your cooking sessions, offers data-driven insights, and makes it easy to share culinary inspiration with friends. Whether you’re a budding chef or a seasoned cook, KitchenLog helps you discover your cooking patterns, improve your skills, and celebrate your culinary achievements.

## Project Overview

KitchenLog is a web application built with Flask (Python) on the backend and standard HTML, CSS, and JavaScript (including Fetch API for dynamic updates) on the frontend. It uses SQLAlchemy for database interaction (SQLite) and Flask-Login/Flask-Bcrypt/Flask-WTF for user authentication and security.

Users can:
- **Store and Manage Recipes:** Add new recipes (manually or via simple import - *future feature*), edit existing ones, and organize them using categories. Recipe ingredients are stored flexibly as a JSON list of strings.
- **Log Cooking Sessions:** Record each cooking instance for owned recipes, including date, optional rating, notes, and an integrated timer to track duration.
- **Analyze Cooking Habits:** Automatically tracks the user's current cooking streak (consecutive days cooked). Displays recent cooking activity. *(Future: Add dashboard with more stats/visualizations).*
- **Share Culinary Success:** Selectively share recipes or stats. *(Sharing implementation details TBD - public links or user-to-user)*.

The application follows a Multi-Page Application (MPA) architecture, where Flask renders distinct HTML pages for major views, enhanced with client-side JavaScript for dynamic content loading (e.g., recipe list) and API interactions (adding/deleting recipes, logging sessions).

## Team Members

| UWA ID   | Name            | GitHub Username                                    
| :------- | :-------------- | :---------------------------------------------
| 23868133 | Alison Barboza  | [BlossomXD1](https://github.com/BlossomXD1)     
| 24078797 | Jason Yulfan    | [jayshira](https://github.com/jayshira)            
| 22965587 | Jiwon Song      | [jiwon-07](https://github.com/jiwon-07)         
| 23769653 | Hunter Wang     | [BiliBiliMay](https://github.com/BiliBiliMay)  

*(Note: Please update Hunter Wang's GitHub username when confirmed.)*

## Key Features

*(Existing Key Features section remains largely the same, but you might want to update it based on the implemented Cooking Log feature vs. the original plan)*

### Introductory View (/)
- Displays a welcome message and provides links/buttons for Login and Sign Up.

### User Authentication (/auth/*)
- Secure user signup and login using Flask-Login, Flask-Bcrypt, and Flask-WTF for validation and CSRF protection.

### My Kitchen View (/home)
- **Recipe Management:**
    - **Add Recipe:** A dedicated tab with a form to add new recipes (name, category, time, ingredients, instructions, optional image). Uses Fetch API for submission.
    - **View Recipes:** Dynamically loaded list/grid of the user's recipes. Includes search functionality.
    - **Edit Recipe:** *(Currently not implemented/functional)* Ability to modify existing recipes.
    - **Delete Recipe:** Button to delete recipes (protected by CSRF, prevents deletion if cooking logs exist).
- **Cooking Log Integration:**
    - **Log Session:** "Cook" button on owned recipes links to a dedicated `/start_cooking/<id>` page.
    - **Session Page:** Displays recipe details, provides an interactive timer, and includes a form to log date cooked, rating, and notes. Submits to `/log_cooking/<id>`.
    - **Recent Activity:** Displays the last few cooking log entries on the main `/home` view.
    - **Cooking Streak:** Displays the user's current consecutive day cooking streak on the main `/home` view.
- **Recipe Stats:** Tab showing basic statistics derived from the user's saved recipes (total count, category distribution, time analysis) with Chart.js visualizations.
- **Share:** Tab allowing users to select a recipe and generate basic sharing information *(Full sharing mechanism TBD)*.

*(Remove references to Visualize Data View /dashboard and Share Data View /share as separate pages if they are now integrated tabs in /home, or update as needed)*

## Technologies Used

- **Frontend:**
    - HTML, CSS, JavaScript
    - Fetch API for AJAX calls
    - Chart.js for data visualizations
- **Backend:**
    - Python 3
    - Flask (including Blueprints)
    - SQLAlchemy (with SQLite)
    - Flask-Login (User session management)
    - Flask-Bcrypt (Password hashing)
    - Flask-WTF (Form handling, CSRF protection)
- **Database:**
    - SQLite (managed via SQLAlchemy)

## Prerequisites

Before you begin, ensure you have the following installed:
- Python (version 3.8 or higher recommended)
- `pip` (Python package installer)
- Git (for cloning the repository)

## Setup Instructions

Follow these steps to set up the project locally:

1.  **Clone the Repository:**
    ```bash
    # Ensure you are cloning your private repository URL
    git clone <your-private-repository-url>
    cd <repository-folder-name> # e.g., cd KitchenLog
    ```

2.  **Create and Activate a Virtual Environment:**
    (Highly Recommended)
    ```bash
    # Create (use 'python3' if needed)
    python -m venv env

    # Activate
    # macOS/Linux:
    source env/bin/activate
    # Windows (Git Bash/WSL):
    # source env/Scripts/activate
    # Windows (Command Prompt):
    # .\env\Scripts\activate.bat
    # Windows (PowerShell):
    # .\env\Scripts\Activate.ps1
    ```
    Your prompt should show `(env)`.

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Setup:**
    The application uses SQLite. The database file (`instance/recipes.db` or `recipes.db` depending on setup) and tables will be automatically created/checked by the `db.create_all()` command in `app/__init__.py` when the application first runs.
    *(Note: If you encounter issues after model changes, you might need to delete the existing `.db` file and let it be recreated, which **will delete all data**.)*

## Running the Application

1.  **Ensure Virtual Environment is Active:**
    ```bash
    source env/bin/activate # Or your OS equivalent
    ```

2.  **Start the Flask Development Server:**
    From the project's root directory (where `run.py` is):
    ```bash
    python run.py
    # Or using the Flask CLI (if configured):
    # flask run
    ```

3.  **Access the Application:**
    Open your web browser and navigate to:
    [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
    You should see the KitchenLog welcome page. Use the links to sign up or log in. The main user dashboard is at `/home` after logging in.

## Running Tests

    we havent written test files...


