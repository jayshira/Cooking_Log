// static/script.js

// Global variables for charts
let categoryChart = null;
let timeChart = null;
let currentRecipes = []; // Cache recipes locally for search/share dropdowns

// --- API Helper Functions ---

async function fetchRecipes() {
    // API endpoint now fetches recipes for the current user (based on session cookie)
    try {
        const response = await fetch('/api/recipes'); // No user ID needed in URL
        if (!response.ok) {
            if (response.status === 401) { // Unauthorized
                 alert("Your session may have expired. Please log in again.");
                 window.location.href = '/login'; // Redirect to login
                 return [];
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const recipes = await response.json();
        currentRecipes = recipes;
        return recipes;
    } catch (error) {
        console.error("Error fetching recipes:", error);
        alert("Failed to load your recipes.");
        currentRecipes = [];
        return [];
    }
}

async function fetchApi(url, options = {}) {
    try {
        const response = await fetch(url, options);
        // ... basic response handling ...
        if (!response.ok) {
             // ... error extraction ...
            throw new Error(`HTTP error! Status: ${response.status} - ${errorMessage}`);
        }
        return data; // Parsed JSON or text
    } catch (error) {
        console.error(`API Error (${options.method || 'GET'} ${url}):`, error);
        throw error; // Rethrow for specific handling
    }
}
// Example usage:
// const recipes = await fetchApi('/api/recipes');
// const newRecipe = await fetchApi('/api/recipes', { method: 'POST', ... });

function showTemporaryStatusMessage(message, type = 'info') {
    const statusDiv = document.createElement('div');
    statusDiv.className = `alert alert-${type}`; // Use existing alert styles
    statusDiv.textContent = message;
    // Style for fixed position at top-center
    statusDiv.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1050; ...';
    document.body.appendChild(statusDiv);
    // Remove after a delay
    setTimeout(() => { /* ... fade out and remove ... */ }, 3000);
}
// Example usage:
// postSaveActions(savedRecipe, ...) { if (savedRecipe) { showTemporaryStatusMessage("Recipe saved!", "success"); } }


function copyRecipeLink() {
    const linkInput = document.getElementById('recipe-share-link');
    if (!linkInput || !linkInput.value) {
        showTemporaryStatusMessage('No recipe link available to copy.', 'warning');
        return;
    }

    linkInput.focus(); // It's often helpful to focus the element first
    linkInput.select(); // Select the text field's content
    linkInput.setSelectionRange(0, 99999); // For mobile device compatibility

    let copied = false; // Flag to track if copy was successful

    // --- Try using execCommand first (legacy method) ---
    try {
        // Attempt to copy using the older execCommand
        copied = document.execCommand('copy');
        if (copied) {
            showTemporaryStatusMessage('Link copied to clipboard!', 'success');
        } else {
            // execCommand is available but returned false (might happen in some cases)
            throw new Error('execCommand returned false');
        }
    } catch (err) {
        console.warn('execCommand copy failed, attempting Clipboard API fallback.', err);

        // --- Fallback using the modern Clipboard API ---
        // Check if the Clipboard API is available
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(linkInput.value)
                .then(() => {
                    // This function runs if writeText() is successful
                    copied = true; // Mark as copied using the modern API
                    showTemporaryStatusMessage('Link copied to clipboard!', 'success');
                })
                .catch(clipboardErr => {
                    // This function runs if writeText() fails (e.g., permissions)
                    console.error('Clipboard API fallback failed:', clipboardErr);
                    showTemporaryStatusMessage('Failed to copy link automatically.', 'danger');
                    // Provide clearer user instruction if both methods fail
                    alert('Could not copy link automatically. Please select the link text and copy it manually (Ctrl+C or Cmd+C).');
                });
        } else {
            // Clipboard API is not supported by the browser
            console.error('Clipboard API not available.');
            showTemporaryStatusMessage('Failed to copy link. Browser does not support clipboard operations.', 'danger');
            alert('Could not copy link automatically. Please select the link text and copy it manually (Ctrl+C or Cmd+C).');
        }
    } finally {
        // Deselect the text after attempting copy, regardless of success/failure
        // Use a small timeout to ensure deselection happens after potential async clipboard operations finish
        setTimeout(() => {
            window.getSelection()?.removeAllRanges(); // Deselect using optional chaining
            // Optionally blur the input field to remove focus visually
            // linkInput.blur();
        }, 100); // 100ms delay
    }
}


async function addRecipeToServer(recipeData) {
    // Get the CSRF token from the meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        console.error("CSRF token not found in meta tag!");
        alert("Action failed: Security token missing. Please refresh the page.");
        return null;
    }

    try {
        const response = await fetch('/api/recipes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken // Include the token in the headers
            },
            body: JSON.stringify(recipeData),
        });
        // ... (rest of the function remains the same) ...
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            if (response.status === 401) { /* ... */ }
            // Check specifically for 400, often related to CSRF or validation issues
            if (response.status === 400 && errorData.error && errorData.error.toLowerCase().includes('csrf')) {
                 alert("Action failed: Security token mismatch. Please refresh the page and try again.");
                 return null;
            }
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.error}`);
        }
        const newRecipe = await response.json();
        currentRecipes.unshift(newRecipe);
        return newRecipe;
    } catch (error) {
        console.error("Error adding recipe:", error);
        alert(`Failed to save recipe: ${error.message}`);
        return null;
    }
}

async function deleteRecipeFromServer(recipeId) {
    // Get the CSRF token from the meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
     if (!csrfToken) {
        console.error("CSRF token not found in meta tag!");
        alert("Action failed: Security token missing. Please refresh the page.");
        return false; // Indicate failure
    }

    try {
        const response = await fetch(`/api/recipes/${recipeId}`, {
            method: 'DELETE',
            headers: { // Add headers object
                'X-CSRFToken': csrfToken // Include the token
            }
        });
        // ... (rest of the function remains the same) ...
         if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
             if (response.status === 401) { /* ... */ }
             if (response.status === 403) { /* ... */ }
             if (response.status === 409) { /* ... */ }
              if (response.status === 400 && errorData.error && errorData.error.toLowerCase().includes('csrf')) {
                 alert("Action failed: Security token mismatch. Please refresh the page and try again.");
                 return false;
             }
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.error}`);
        }
        currentRecipes = currentRecipes.filter(r => r.id !== recipeId);
        return true;
    } catch (error) {
        console.error(`Error deleting recipe ${recipeId}:`, error);
        alert(`Failed to delete recipe: ${error.message}`);
        return false;
    }
}

async function deleteRecipeFromServer(recipeId) {
    // No changes needed here, authorization is handled by backend
     try {
        const response = await fetch(`/api/recipes/${recipeId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
             if (response.status === 401) {
                 alert("Your session may have expired. Please log in again.");
                 window.location.href = '/login';
                 return false;
             }
             if (response.status === 403) { // Forbidden
                throw new Error(`Authorization error: ${errorData.error}`);
             }
             if (response.status === 409) { // Conflict (e.g., recipe has logs)
                 throw new Error(`${errorData.error}`); // Display the specific error from backend
             }
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.error}`);
        }
        currentRecipes = currentRecipes.filter(r => r.id !== recipeId);
        return true;
    } catch (error) {
        console.error(`Error deleting recipe ${recipeId}:`, error);
        // Display specific error message from backend if available
        alert(`Failed to delete recipe: ${error.message}`);
        return false;
    }
}

// --- UI Rendering ---

// Function to render a single recipe card
function renderRecipeCard(recipe) {
    const recipeCard = document.createElement('div');
    recipeCard.className = 'recipe-card';
    recipeCard.dataset.id = recipe.id; // Keep data-id for delete/view

    const ingredientsPreview = (Array.isArray(recipe.ingredients) ? recipe.ingredients : []) // Ensure it's an array
                               .slice(0, 4).join(', ') + (recipe.ingredients.length > 4 ? '...' : '');
    const imageStyle = recipe.image
        ? `background-image: url(${recipe.image});`
        : 'background-image: linear-gradient(135deg, var(--primary-color), var(--secondary-color));'; // Default gradient

    // Determine if current user owns this recipe (needed for button visibility)
    // Assumes CURRENT_USER_ID is available globally from the template
    const isOwner = typeof CURRENT_USER_ID !== 'undefined' && recipe.user_id === CURRENT_USER_ID;

    recipeCard.innerHTML = `
        <div class="recipe-img" style="${imageStyle}"></div>
        <div class="recipe-info">
            <h3 class="recipe-title">${recipe.name}</h3>
            <div class="recipe-meta">
                <span><i class="fas fa-tag category-icon"></i> ${recipe.category}</span>
                <span><i class="fas fa-clock time-icon"></i> ${recipe.time} mins</span>
            </div>
            <p class="recipe-ingredients-preview">
                <strong>Ingredients:</strong> ${ingredientsPreview || 'No ingredients listed'}
            </p>
            <div class="recipe-actions">
                <!-- View Button (always visible maybe?) -->
                <button class="btn btn-secondary btn-sm" onclick="viewRecipe(${recipe.id})">
                    <i class="fas fa-eye"></i> View
                </button>

                ${isOwner ? `
                <!-- Start Cooking Button (only for owner) -->
                <a href="/start_cooking/${recipe.id}" class="btn btn-success btn-sm">
                    <i class="fas fa-utensils"></i> Cook
                </a>
                <!-- Delete Button (only for owner) -->
                <button class="btn btn-danger btn-sm" onclick="deleteRecipe(${recipe.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
                ` : ''}
            </div>
        </div>
    `;
    return recipeCard;
}

// Load recipes into the UI and Share dropdown
async function loadRecipes() {
    const recipeList = document.getElementById('recipe-list');
    const shareRecipeSelect = document.getElementById('share-recipe');

    // Clear previous content and show loading indicators
    recipeList.innerHTML = '<p style="grid-column: 1/-1; text-align: center;"><i class="fas fa-spinner fa-spin"></i> Loading your recipes...</p>';
    // Check if shareRecipeSelect exists before manipulating
    if (shareRecipeSelect) {
        shareRecipeSelect.innerHTML = '<option value="">Loading...</option>';
        shareRecipeSelect.disabled = true;
    }
    const sharePreview = document.getElementById('share-preview');
    if (sharePreview) {
        sharePreview.style.display = 'none';
    }

    const recipes = await fetchRecipes(); // Fetches recipes for the logged-in user

    recipeList.innerHTML = ''; // Clear loading indicator
    if (shareRecipeSelect) {
        shareRecipeSelect.innerHTML = '<option value="">Select a recipe to share</option>'; // Reset dropdown
    }

    if (recipes.length === 0) {
        recipeList.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--grey);">You haven\'t added any recipes yet. Use the "Add Recipe" tab!</p>';
        if (shareRecipeSelect) {
            shareRecipeSelect.disabled = true; // Keep disabled if no recipes
        }
    } else {
        recipes.forEach(recipe => {
            const recipeCard = renderRecipeCard(recipe);
            recipeList.appendChild(recipeCard);

            // Add to share dropdown only if the user owns the recipe and the select exists
             if (shareRecipeSelect && typeof CURRENT_USER_ID !== 'undefined' && recipe.user_id === CURRENT_USER_ID) {
                const option = document.createElement('option');
                option.value = recipe.id;
                option.textContent = recipe.name;
                shareRecipeSelect.appendChild(option);
             }
        });
         // Enable share dropdown only if options were added and the select exists
         if (shareRecipeSelect) {
             shareRecipeSelect.disabled = shareRecipeSelect.options.length <= 1;
         }
    }

    // Update stats based on the fetched recipes
    updateStats();
    checkShareDropdown(); // Ensure consistency after potential deletion/reload
}

// Check share dropdown state (helper function)
function checkShareDropdown() {
    const shareRecipeSelect = document.getElementById('share-recipe');
    if (!shareRecipeSelect) return; // Exit if the dropdown doesn't exist on the page

    const currentShareId = shareRecipeSelect.value;
    const sharePreview = document.getElementById('share-preview');

    if (currentShareId && !currentRecipes.some(r => r.id == currentShareId)) {
         if (sharePreview) sharePreview.style.display = 'none';
         shareRecipeSelect.value = '';
         shareRecipeSelect.disabled = shareRecipeSelect.options.length <= 1;
    } else if (currentShareId && sharePreview) {
        // Refresh preview if still valid
         displaySharePreview(currentShareId);
    } else if (sharePreview) {
        sharePreview.style.display = 'none';
    }
}

// --- Event Handlers ---

// Handle form submission
async function handleFormSubmit(event) {
    event.preventDefault();

    const name = document.getElementById('recipe-name').value.trim();
    const category = document.getElementById('recipe-category').value;
    const timeInput = document.getElementById('recipe-time').value;
    const ingredientsText = document.getElementById('recipe-ingredients').value.trim(); // Get raw text
    const instructions = document.getElementById('recipe-instructions').value.trim();
    const imageInput = document.getElementById('recipe-image');

    if (!name || !category || !timeInput || !ingredientsText || !instructions) {
         alert('Please fill in all required fields.');
         return;
    }
    const time = parseInt(timeInput, 10);
     if (isNaN(time) || time <= 0) {
         alert('Please enter a valid positive number for time.');
         return;
     }

     // Smart ingredient parsing: handles commas and newlines
     const ingredientsList = ingredientsText
        .split(/[\\n,]+/) // Split by newline OR comma
        .map(i => i.trim()) // Trim whitespace
        .filter(i => i); // Remove empty lines/items

    const newRecipeData = {
        name,
        category,
        time,
        ingredients: ingredientsList, // Send as an array
        instructions,
        date: new Date().toISOString().split('T')[0], // Just date part
        image: null
    };

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...'; // Add saving icon

    if (imageInput.files.length > 0) {
        const reader = new FileReader();
        reader.onload = async function(e) {
            newRecipeData.image = e.target.result; // Base64 string
            const savedRecipe = await addRecipeToServer(newRecipeData);
            postSaveActions(savedRecipe, submitButton);
        };
        reader.onerror = function() {
            console.error("Error reading file");
            alert("Error reading image file. Saving recipe without image.");
            addRecipeToServer(newRecipeData).then(savedRecipe => postSaveActions(savedRecipe, submitButton));
        };
        reader.readAsDataURL(imageInput.files[0]); // Read as Base64
    } else {
        const savedRecipe = await addRecipeToServer(newRecipeData);
        postSaveActions(savedRecipe, submitButton);
    }
}

// Actions to take after trying to save a recipe
function postSaveActions(savedRecipe, submitButton) {
     submitButton.disabled = false;
     submitButton.innerHTML = '<i class="fas fa-save"></i> Save Recipe'; // Reset button text/icon

    if (savedRecipe) {
        document.getElementById('recipe-form').reset();
        const fileUploadStatus = document.getElementById('file-upload-status');
        document.getElementById('recipe-image').value = '';
        if (fileUploadStatus) {
            fileUploadStatus.textContent = '';
            fileUploadStatus.className = '';
        }

        // Reload recipes which now includes the new one
        loadRecipes();
        // Switch to the 'My Recipes' tab to show the new card
        switchTab('my-recipes'); // Use the new tab ID
        // Give specific success feedback
        // Flash message will appear on reload/redirect if backend sends one,
        // but an alert gives immediate feedback here.
        alert(`Recipe "${savedRecipe.name}" saved successfully!`);
    } else {
        // Error alerts handled within addRecipeToServer
    }
}

// Delete recipe function (called by button)
async function deleteRecipe(id) {
    // Find recipe name for confirmation message
    const recipe = currentRecipes.find(r => r.id === id);
    const recipeName = recipe ? `"${recipe.name}"` : "this recipe";

    if (confirm(`Are you sure you want to delete ${recipeName}? This cannot be undone.`)) {
        const success = await deleteRecipeFromServer(id);
        if (success) {
            // Reload recipes to update list, stats, and dropdowns
            loadRecipes();
            // No alert needed here, as the error function shows one on failure
        }
    }
}

// View recipe details (uses local cache)
function viewRecipe(id) {
    const recipe = currentRecipes.find(r => r.id == id);

    if (recipe) {
        let ingredientsString = "No ingredients listed.";
        if (recipe.ingredients && Array.isArray(recipe.ingredients) && recipe.ingredients.length > 0) {
            ingredientsString = "- " + recipe.ingredients.join('\n- ');
        } else if (typeof recipe.ingredients === 'string' && recipe.ingredients.trim()) {
             // Fallback if somehow it's still a string
             ingredientsString = recipe.ingredients;
        }

        alert(`
--------------------
RECIPE: ${recipe.name}
--------------------
Category: ${recipe.category}
Time: ${recipe.time} minutes
Added/Updated: ${recipe.date} ${recipe.author ? '\nAuthor: '+recipe.author : ''}

INGREDIENTS:
${ingredientsString}

INSTRUCTIONS:
${recipe.instructions || 'No instructions provided.'}
--------------------
        `);
    } else {
        alert('Recipe details not found. The list might be updating, please try again shortly.');
    }
}

// Display share preview (uses local cache)
function displaySharePreview(recipeId) {
     const sharePreview = document.getElementById('share-preview');
     if (!sharePreview) return; // Exit if share section isn't on page

     const recipe = currentRecipes.find(r => r.id == recipeId); // Find in local cache

     if (recipe) {
         sharePreview.style.display = 'block';
         document.getElementById('share-title').textContent = recipe.name;
         document.getElementById('share-category').innerHTML = `<i class="fas fa-tag category-icon"></i> ${recipe.category}`;
         document.getElementById('share-time').innerHTML = `<i class="fas fa-clock time-icon"></i> ${recipe.time} mins`;

         const shareImage = document.getElementById('share-image');
         if (shareImage) {
             shareImage.style.backgroundImage = recipe.image
                 ? `url(${recipe.image})`
                 : 'linear-gradient(135deg, var(--primary-color), var(--secondary-color))';
         }
     } else {
         sharePreview.style.display = 'none';
     }
}

// --- Stats and Charts (uses local cache) ---

function updateStats() {
    const recipes = currentRecipes; // Use the cached data
    const totalRecipes = recipes.length;

    // Check if stat elements exist before updating
    const totalRecipesEl = document.getElementById('total-recipes');
    const mostCookedEl = document.getElementById('most-cooked');
    const totalTimeEl = document.getElementById('total-time');
    const avgTimeEl = document.getElementById('avg-time');

    if (totalRecipesEl) totalRecipesEl.textContent = totalRecipes;

    if (totalRecipes > 0) {
        const categoryCounts = recipes.reduce((acc, recipe) => {
            acc[recipe.category] = (acc[recipe.category] || 0) + 1;
            return acc;
        }, {});
        const mostCommonCategory = Object.keys(categoryCounts).reduce((a, b) =>
            categoryCounts[a] > categoryCounts[b] ? a : b, Object.keys(categoryCounts)[0] || '-'
        );
         if (mostCookedEl) mostCookedEl.textContent = mostCommonCategory || '-';

        const totalTime = recipes.reduce((sum, recipe) => sum + (recipe.time || 0), 0); // Ensure time exists
        const avgTime = totalRecipes > 0 ? totalTime / totalRecipes : 0;
        if (totalTimeEl) totalTimeEl.textContent = totalTime;
        if (avgTimeEl) avgTimeEl.textContent = avgTime.toFixed(1);

        // Check if chart canvases exist before updating
        if (document.getElementById('category-chart')) {
             updateCategoryChart(categoryCounts);
        }
        if (document.getElementById('time-chart')) {
            updateTimeChart(recipes);
        }

    } else {
        if (mostCookedEl) mostCookedEl.textContent = '-';
        if (totalTimeEl) totalTimeEl.textContent = '0';
        if (avgTimeEl) avgTimeEl.textContent = '0';

        // Clear charts if no data
        if (document.getElementById('category-chart')) {
            updateCategoryChart({});
        }
        if (document.getElementById('time-chart')) {
            updateTimeChart([]);
        }
    }
}

// --- Chart Update Functions --- 
function updateCategoryChart(categoryCounts) {
    const ctx = document.getElementById('category-chart')?.getContext('2d');
    if (!ctx) return; // Exit if canvas not found

    const labels = Object.keys(categoryCounts);
    const data = Object.values(categoryCounts);

    const backgroundColors = [
        '#FF7B54', '#FFB26B', '#FFD56F', '#939B62', '#4E8C87', '#6B5B95',
        '#F7CAC9', '#92A8D1', '#F4A261', '#E76F51', '#2A9D8F', '#264653'
    ];

    if (categoryChart) {
        categoryChart.destroy();
    }

    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Recipes per Category',
                data: data,
                backgroundColor: backgroundColors.slice(0, labels.length),
                borderColor: 'var(--white)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12, padding: 15 } },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) { label += ': '; }
                            if (context.parsed !== null) { label += context.parsed; }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

function updateTimeChart(recipes) {
    const ctx = document.getElementById('time-chart')?.getContext('2d');
    if (!ctx) return; // Exit if canvas not found

    const timeRanges = [
        { label: '0-15 min', min: 0, max: 15 }, { label: '16-30 min', min: 16, max: 30 },
        { label: '31-45 min', min: 31, max: 45 }, { label: '46-60 min', min: 46, max: 60 },
        { label: '60+ min', min: 61, max: Infinity }
    ];

    const timeData = timeRanges.map(range =>
        recipes.filter(r => (r.time || 0) >= range.min && (r.time || 0) <= range.max).length
    );
    const labels = timeRanges.map(r => r.label);
    const backgroundColors = ['#FF7B54', '#FFB26B', '#FFD56F', '#939B62', '#4E8C87'];

    if (timeChart) {
        timeChart.destroy();
    }

    timeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Recipes', data: timeData,
                backgroundColor: backgroundColors, borderColor: backgroundColors.map(c => c + 'B3'),
                borderWidth: 1, borderRadius: 4,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, color: 'var(--grey)' }, grid: { color: '#eee' } },
                x: { ticks: { color: 'var(--grey)' }, grid: { display: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: 'var(--dark-color)', titleColor: 'var(--white)', bodyColor: 'var(--white)' }
            }
        }
    });
}

// --- Utility and Event Listeners Setup ---

// Function to switch tabs programmatically
function switchTab(tabId) {
     const targetTab = document.querySelector(`.tab[data-tab="${tabId}"]`);
     if (targetTab && !targetTab.classList.contains('active')) {
         targetTab.click(); // Simulate click to trigger listener
     }
}

// Handle file input change for immediate feedback
function handleFileChange(fileInput) {
    const fileUploadStatus = document.getElementById('file-upload-status');
    if (!fileUploadStatus) return; // Exit if status element doesn't exist

    if (fileInput.files.length > 0) {
        const fileName = fileInput.files[0].name;
        const fileSize = (fileInput.files[0].size / 1024 / 1024).toFixed(2); // Size in MB
        // Basic validation (e.g., check file type/size)
        if (fileSize > 5) { // Example: Limit to 5MB
            fileUploadStatus.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: var(--danger-color);"></i> File too large: ${fileName} (${fileSize}MB). Max 5MB.`;
            fileUploadStatus.className = 'danger';
            fileInput.value = ''; // Clear the input
            return;
        }
        if (!fileInput.files[0].type.startsWith('image/')) {
             fileUploadStatus.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: var(--danger-color);"></i> Invalid file type: ${fileName}. Please upload an image.`;
             fileUploadStatus.className = 'danger';
             fileInput.value = ''; // Clear the input
             return;
        }

        fileUploadStatus.innerHTML = `<i class="fas fa-check-circle" style="color: var(--success-color);"></i> File selected: ${fileName} (${fileSize}MB)`;
        fileUploadStatus.className = 'success';
    } else {
        fileUploadStatus.textContent = '';
        fileUploadStatus.className = '';
    }
}

// Share recipe via different platforms
function shareRecipe(platform) {
    const shareRecipeSelect = document.getElementById('share-recipe');
    if (!shareRecipeSelect) return;

    const recipeId = shareRecipeSelect.value;
    if (!recipeId) {
        alert('Please select a recipe to share first.');
        return;
    }
    // Find recipe in local cache for sharing details
    const recipe = currentRecipes.find(r => r.id == recipeId);
    if (!recipe) {
        alert('Selected recipe details not found.');
        return;
    }

    const shareText = `Check out my recipe for "${recipe.name}"! Prep time: ${recipe.time} mins. Category: ${recipe.category}.`;
    const appUrl = window.location.origin; // Base URL of the app
    // Construct a more specific URL if you have public recipe pages later
    // const recipeUrl = `${appUrl}/recipe/${recipe.id}`; // Example
    const recipeUrl = appUrl; // For now, just link to the app

    const shareSubject = `My KitchenLog Recipe: ${recipe.name}`;
    let ingredientsList = Array.isArray(recipe.ingredients) ? recipe.ingredients.join('\n- ') : recipe.ingredients;
    const shareBody = `${shareText}\n\nIngredients:\n- ${ingredientsList}\n\nInstructions:\n${recipe.instructions}\n\nShared from my KitchenLog: ${recipeUrl}`;
    let shareUrl = '';

    switch (platform) {
        case 'facebook':
            // FB Sharer needs a real URL to scrape, using appUrl for now
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(recipeUrl)}"e=${encodeURIComponent(shareText)}`;
            break;
        case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(recipeUrl)}`;
            break;
        case 'whatsapp':
            // WhatsApp Web/App link
            shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText + ' Shared from KitchenLog: ' + recipeUrl)}`;
            break;
        case 'email':
            shareUrl = `mailto:?subject=${encodeURIComponent(shareSubject)}&body=${encodeURIComponent(shareBody)}`;
            break;
        default: return;
    }
    if (shareUrl) {
        window.open(shareUrl, '_blank', 'noopener,noreferrer,width=600,height=400');
    }
}

// --- Initial Setup ---
document.addEventListener('DOMContentLoaded', function() {

    // Tab switching
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
             // If the tab is disabled, do nothing
            if (tab.classList.contains('disabled')) return;

            const tabId = tab.getAttribute('data-tab');
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            tabContents.forEach(c => c.classList.remove('active'));

            const activeContent = document.getElementById(tabId);
             if (activeContent) {
                 activeContent.classList.add('active');
                 // Update recipe stats only when that specific tab is viewed
                 if (tabId === 'recipe-stats') {
                     updateStats(); // Re-calculate stats based on currentRecipes
                 }
             } else {
                 // console.warn(`Tab content with ID "${tabId}" not found.`);
             }
        });
    });

    // File upload trigger & feedback
    const fileUploadArea = document.getElementById('file-upload');
    if (fileUploadArea) { // Check if the element exists (it's inside a tab)
        const fileInputElement = document.getElementById('recipe-image');
        fileUploadArea.addEventListener('click', () => fileInputElement.click());
        // Drag and Drop Handling
        fileUploadArea.addEventListener('dragover', (event) => {
            event.preventDefault(); // Necessary to allow drop
            fileUploadArea.style.borderColor = 'var(--primary-color)';
            fileUploadArea.style.backgroundColor = 'rgba(255, 123, 84, 0.05)';
        });
        fileUploadArea.addEventListener('dragleave', () => {
             fileUploadArea.style.borderColor = 'var(--light-grey)';
             fileUploadArea.style.backgroundColor = '#fafafa';
        });
        fileUploadArea.addEventListener('drop', (event) => {
            event.preventDefault();
            fileUploadArea.style.borderColor = 'var(--light-grey)';
            fileUploadArea.style.backgroundColor = '#fafafa';
            if (event.dataTransfer.files.length > 0) {
                fileInputElement.files = event.dataTransfer.files; // Assign dropped files
                handleFileChange(fileInputElement); // Update UI
            }
        });
        fileInputElement.addEventListener('change', () => handleFileChange(fileInputElement));
    }

    // Recipe form submission listener
    const recipeForm = document.getElementById('recipe-form');
    if (recipeForm) {
        recipeForm.addEventListener('submit', handleFormSubmit);
    }

    // Search functionality
    const searchInput = document.getElementById('recipe-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const recipeListContainer = document.getElementById('recipe-list');
            let visibleCount = 0;
            let noResultMessage = recipeListContainer.querySelector('.no-search-results');

             // Remove existing no-results message before filtering
             if (noResultMessage) noResultMessage.remove();

            currentRecipes.forEach(recipe => {
                const card = recipeListContainer.querySelector(`.recipe-card[data-id='${recipe.id}']`);
                if (!card) return;

                const title = recipe.name.toLowerCase();
                const ingredientsText = (Array.isArray(recipe.ingredients) ? recipe.ingredients.join(', ') : '').toLowerCase();
                const categoryText = recipe.category.toLowerCase();
                const isMatch = title.includes(searchTerm) || ingredientsText.includes(searchTerm) || categoryText.includes(searchTerm);

                card.style.display = isMatch ? '' : 'none';
                if (isMatch) visibleCount++;
            });

            // Add "no results" message if needed AFTER filtering
            if (visibleCount === 0 && currentRecipes.length > 0) {
                noResultMessage = document.createElement('p');
                noResultMessage.className = 'no-search-results';
                noResultMessage.style.cssText = 'grid-column: 1 / -1; text-align: center; color: var(--grey); margin-top: 15px;';
                noResultMessage.textContent = `No recipes found matching "${searchTerm}".`;
                recipeListContainer.appendChild(noResultMessage);
            } else if (visibleCount === 0 && currentRecipes.length === 0 && searchTerm === '') {
                 // Handle case where list is empty initially and search is cleared
                 if (!recipeListContainer.querySelector('p')) { // Avoid adding if initial empty message exists
                     recipeListContainer.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--grey);">You haven\'t added any recipes yet. Use the "Add Recipe" tab!</p>';
                 }
            }
        });
    }

    // Share recipe selection listener
    const shareRecipeSelect = document.getElementById('share-recipe');
    if (shareRecipeSelect) {
        shareRecipeSelect.addEventListener('change', function() {
            displaySharePreview(this.value);
        });
    }

    // Initial load of recipes (for the logged-in user)
    // Check if the recipe list container exists before loading
    // This assumes script.js is loaded on pages where #recipe-list is present
    if (document.getElementById('recipe-list')) {
        loadRecipes();
    }

}); // End DOMContentLoaded