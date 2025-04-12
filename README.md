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
