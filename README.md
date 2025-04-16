# KitchenLog

**KitchenLog** is your personal digital cookbook and cooking diary that not only serves as a repository for your favorite recipes but also tracks your cooking sessions, offers data-driven insights, and makes it easy to share culinary inspiration with friends. Whether you’re a budding chef or a seasoned cook, KitchenLog helps you discover your cooking patterns, improve your skills, and celebrate your culinary achievements.

## Project Overview

KitchenLog is a web application that allows users to:
- **Store and Manage Recipes:** Add new recipes (manually or via simple import), edit existing ones, and organize them using tags/cuisines.
- **Log Cooking Sessions:** Record each cooking instance with options to rate, add session notes, and even set a timer to track the duration.
- **Analyze Cooking Habits:** Automatically generate statistics about your cooking frequency, most cooked dishes, average ratings, and your current cooking streak (i.e., how many days in a row you’ve cooked).
- **Share Culinary Success:** Selectively share recipes, cooking logs, or insightful stat snapshots with friends. A dedicated share link feature allows recipients to directly import recipes into their own KitchenLog accounts.

## Key Features

### Introductory View (/)
- **Warm, Inviting Design:** Features kitchen-inspired imagery, clear typography, and a prominent logo.
- **User Onboarding:** Includes a headline, brief description, and immediate access to login and sign-up forms.

### My Kitchen View (/mykitchen)
- **Recipe Management:**
  - **Create & Edit:** Easily add new recipes or modify existing ones with fields for title, description, prep time, cook time, ingredients, instructions, and tags.
  - **Dynamic List:** A searchable/filterable grid/list displays your recipes with options to edit or delete.
- **Cooking Log:**
  - **Log Cooking Sessions:** Select a recipe, log details such as date cooked, actual time spent, and rate your session.
  - **Session Timer:** Integrated timer functionality to track the length of each cooking session.
  - **Cooking Streak:** Automatically count the number of consecutive days the user has cooked.
  - **Instant Feedback:** Confirmation messages and a recent activity log for quick reference.

### Visualize Data View (/dashboard or /insights)
- **Interactive Dashboard:** Offers a set of analytics including:
  - **Key Metrics:** Total meals logged, unique recipes cooked, average ratings, and current cooking streak.
  - **Visualizations:** Charts such as bar graphs for most frequently cooked recipes, line charts/calendar heatmaps for cooking frequency, pie charts for cuisine breakdown, and rating distribution charts.
  - **Detailed Journal:** A filterable history of all cooking sessions for a closer look at your culinary journey.
- **Shared Content:** A dedicated section to view and interact with content shared by your friends.

### Share Data View (/share)
- **Flexible Sharing Options:** Users can choose to share:
  - A complete recipe.
  - Specific cooking log entries.
  - A snapshot of their cooking stats.
- **Share Links:** Users can generate shareable links that let recipients import recipes directly into their own KitchenLog accounts.
- **Manage Shares:** Easily view, manage, and revoke shared items.

## Technologies Used

- **Frontend:**
  - HTML, CSS, JavaScript
  - [Bootstrap](https://getbootstrap.com/) (or Tailwind/SemanticUI/Foundation as chosen)
  - jQuery for dynamic DOM manipulation and AJAX calls
  - Chart.js (or equivalent) for interactive data visualizations

- **Backend:**
  - Flask as the web framework
  - Flask-Login for managing user authentication
  - AJAX/WebSockets for asynchronous data exchange
  - SQLite managed via SQLAlchemy as the database
 
## Prerequisites

Before you begin, ensure you have the following installed:
- Python (version 3.8 or higher recommended)
- `pip` (Python package installer, usually included with Python)
- Git (for cloning the repository)

## Setup Instructions

Follow these steps to set up the project locally:

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url> # Replace with your actual repository URL
    cd KitchenLog # Or your repository's folder name
    ```

2.  **Create and Activate a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.

    ```bash
    # Create the virtual environment (use 'python3' if 'python' links to Python 2)
    python -m venv env

    # Activate the virtual environment:
    # On macOS/Linux (bash/zsh):
    source env/bin/activate
    # On Windows (Command Prompt):
    # .\env\Scripts\activate
    # On Windows (PowerShell):
    # .\env\Scripts\Activate.ps1
    ```
    Your terminal prompt should now show `(env)` at the beginning.

3.  **Install Dependencies:**
    Install all the required Python packages listed in `requirements.txt`. Make sure your virtual environment is active before running this command.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Setup:**
    The application uses SQLite. The database file (`recipes.db`) and the necessary tables (`User`, `Recipe`) will be automatically created in the project's root directory the first time you run the application, thanks to the `db.create_all()` command within the app factory (`app/__init__.py`).
    *(Note: For more complex database changes later, integrating Flask-Migrate is recommended.)*
## Running the Application

1.  **Ensure Virtual Environment is Active:**
    If you haven't already, activate the virtual environment:
    ```bash
    source env/bin/activate # Or your OS equivalent
    ```

2.  **Start the Flask Development Server:**
    Run the `run.py` script from the project's root directory:
    ```bash
    python run.py
    ```

3.  **Access the Application:**
    Open your web browser and navigate to:
    [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
    (Or `http://localhost:5000/`)

    You should see the KitchenLog homepage. You can now sign up for an account and log in.

## Project Structure

```text
KitchenLog/
├── app/
│   ├── static/
│   │   ├── script.js
│   │   └── style.css
│   ├── templates/
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── signup.html
│   │   └── index.html
│   ├── __init__.py     # Application Factory
│   ├── auth.py         # Authentication routes (auth blueprint)
│   ├── models.py       # Database models
│   └── routes.py       # Main application routes (main blueprint)
├── env/                # Virtual environment directory
├── config.py           # Configuration settings
├── recipes.db          # SQLite database file
├── requirements.txt    # Python dependencies
├── run.py              # Script to run the Flask application
├── README.md           # This file
└── LICENSE             # (Optional) License file

