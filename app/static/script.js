// static/script.js

// Global variables for charts
let topRecipesChart = null;
let frequencyChart = null;
let topRatedChart = null;
let chartStates = {
    'top-recipes': 'all-time',
    'frequency': 'monthly',
    'top-rated': 'all-time'
};
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

// static/script.js
function showTemporaryStatusMessage(message, type = 'info', duration = 3000) {
    const statusDiv = document.createElement('div');
    statusDiv.className = `alert alert-${type}`;
    statusDiv.textContent = message;
    
    // Base styles
    statusDiv.style.position = 'fixed';
    statusDiv.style.top = '20px';
    statusDiv.style.left = '50%';
    statusDiv.style.transform = 'translateX(-50%)';
    statusDiv.style.zIndex = '1050';
    statusDiv.style.padding = '10px 20px'; // Ensure padding
    statusDiv.style.borderRadius = '5px'; // Ensure border-radius
    statusDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)'; // Add some shadow
    statusDiv.style.opacity = '1';
    statusDiv.style.transition = 'opacity 0.5s ease-out'; // For fade-out

    // Apply alert-specific styles if not already covered by global .alert classes
    // This ensures the background and text colors are set correctly if .alert-{type} isn't globally sufficient
    switch (type) {
        case 'success':
            statusDiv.style.backgroundColor = 'var(--success-bg)'; statusDiv.style.color = 'var(--success-text)'; statusDiv.style.borderColor = 'var(--success-border)';
            break;
        case 'warning':
            statusDiv.style.backgroundColor = 'var(--warning-bg)'; statusDiv.style.color = 'var(--warning-text)'; statusDiv.style.borderColor = 'var(--warning-border)';
            break;
        case 'danger':
            statusDiv.style.backgroundColor = 'var(--danger-bg)'; statusDiv.style.color = 'var(--danger-text)'; statusDiv.style.borderColor = 'var(--danger-border)';
            break;
        case 'info':
        default:
            statusDiv.style.backgroundColor = 'var(--info-bg)'; statusDiv.style.color = 'var(--info-text)'; statusDiv.style.borderColor = 'var(--info-border)';
            break;
    }
    
    document.body.appendChild(statusDiv);

    setTimeout(() => {
        statusDiv.style.opacity = '0'; // Start fade-out
        // Remove from DOM after transition completes
        setTimeout(() => {
            if (statusDiv.parentNode) {
                statusDiv.parentNode.removeChild(statusDiv);
            }
        }, 500); // Match transition duration
    }, duration);
}


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

/* COMMENTED OUT SINCE TWO OF THE SAME FUNCTION IS MADE (I WON'T DELETE THE OLD ONE BECAUSE IT'S NOT MY CODE) - jason*/
// async function deleteRecipeFromServer(recipeId) {
//     // No changes needed here, authorization is handled by backend
//      try {
//         const response = await fetch(`/api/recipes/${recipeId}`, {
//             method: 'DELETE',
//         });
//         if (!response.ok) {
//             const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
//              if (response.status === 401) {
//                  alert("Your session may have expired. Please log in again.");
//                  window.location.href = '/login';
//                  return false;
//              }
//              if (response.status === 403) { // Forbidden
//                 throw new Error(`Authorization error: ${errorData.error}`);
//              }
//              if (response.status === 409) { // Conflict (e.g., recipe has logs)
//                  throw new Error(`${errorData.error}`); // Display the specific error from backend
//              }
//             throw new Error(`HTTP error! status: ${response.status} - ${errorData.error}`);
//         }
//         currentRecipes = currentRecipes.filter(r => r.id !== recipeId);
//         return true;
//     } catch (error) {
//         console.error(`Error deleting recipe ${recipeId}:`, error);
//         // Display specific error message from backend if available
//         alert(`Failed to delete recipe: ${error.message}`);
//         return false;
//     }
// }

// --- UI Rendering ---

// Function to render a single recipe card
function renderRecipeCard(recipe) {
    const recipeCard = document.createElement('div');
    recipeCard.className = 'recipe-card';
    recipeCard.dataset.id = recipe.id;

    const ingredientsPreview = (Array.isArray(recipe.ingredients) ? recipe.ingredients : [])
        .slice(0, 4).join(', ') + (recipe.ingredients.length > 4 ? '...' : '');
    
    const imageStyle = recipe.image
        ? `background-image: url(${recipe.image});`
        : 'background-image: linear-gradient(135deg, var(--primary-color), var(--secondary-color));';

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
                <!-- View Button (always visible) -->
                <a href="/view_recipe/${recipe.id}" class="btn btn-secondary btn-sm">
                    <i class="fas fa-eye"></i> View
                </a>

                <!-- Edit Button (only for owner) -->
                ${typeof CURRENT_USER_ID !== 'undefined' && recipe.user_id === CURRENT_USER_ID ? `
                <button class="btn btn-primary btn-sm" onclick="editRecipe(${recipe.id})">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <a href="/start_cooking/${recipe.id}" class="btn btn-success btn-sm">
                    <i class="fas fa-utensils"></i> Cook
                </a>
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

    // Get form values (same as before)
    const name = document.getElementById('recipe-name').value.trim();
    const category = document.getElementById('recipe-category').value;
    const timeInput = document.getElementById('recipe-time').value;
    // const ingredientsText = document.getElementById('recipe-ingredients').value.trim();
    const instructions = document.getElementById('recipe-instructions').value.trim();
    const imageInput = document.getElementById('recipe-image');

    // Validation (same as before)
    // ...

    const time = parseInt(timeInput, 10);
    // ... more validation ...

    // const ingredientsList = ingredientsText.split(/[\n,]+/).map(i => i.trim()).filter(i => i);

    const ingredientsList = Array.from(
        document.querySelectorAll('#ingredient-list li span')
    ).map(span => span.textContent.trim());

    const form = document.getElementById('recipe-form');
    const isEditing = form.dataset.editingId;

    // Base recipe data, DO NOT include image initially
    const recipeData = {
        name,
        category,
        time,
        ingredients: ingredientsList,
        instructions,
        // date: new Date().toISOString().split('T')[0], // Backend handles date on creation, less needed on update
        // image: null // <-- REMOVE THIS INITIAL NULL VALUE
    };

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    // Flag to track if a new image was processed
    let newImageProcessed = false;

    // Handle image ONLY IF a new file is selected
    if (imageInput.files.length > 0) {
        // Create a promise to handle FileReader async operation
        const imagePromise = new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                recipeData.image = e.target.result; // Add image data ONLY if read successfully
                newImageProcessed = true;
                resolve(); // Resolve the promise after setting image data
            };
            reader.onerror = function() {
                console.error("Error reading file");
                // Decide if you want to proceed without image or reject
                // alert("Error reading image file. Proceeding without updating image.");
                // reject(new Error("Error reading image file")); // Option 1: Stop the process
                resolve(); // Option 2: Continue without the new image
            };
            reader.readAsDataURL(imageInput.files[0]);
        });

        // Wait for the image processing to complete before saving
        try {
            await imagePromise;
            await saveRecipe(recipeData, isEditing, submitButton);
        } catch (error) {
            // Handle FileReader error if promise was rejected
            alert(`Failed to process image: ${error.message}`);
            postSaveActions(null, submitButton); // Indicate failure
        }

    } else {
        // No new file selected, proceed to save without image data
        // The 'image' key will NOT be in recipeData
        await saveRecipe(recipeData, isEditing, submitButton);
    }
}

async function saveRecipe(recipeData, isEditing, submitButton) {
    let savedRecipe;
    try {
        if (isEditing) {
            // Update existing recipe
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            if (!csrfToken) {
                console.error("CSRF token not found in meta tag!");
                alert("Action failed: Security token missing. Please refresh the page.");
                submitButton.disabled = false;
                return;
            }
        
            const response = await fetch(`/api/recipes/${isEditing}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(recipeData)
            });
        
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        
            savedRecipe = await response.json();
            const index = currentRecipes.findIndex(r => r.id == isEditing);
            if (index !== -1) {
                currentRecipes[index] = savedRecipe;
            }
        } else {
            // ADD NEW recipe (POST)
            savedRecipe = await addRecipeToServer(recipeData);
        }
        
        

        postSaveActions(savedRecipe, submitButton);
    } catch (error) {
        console.error("Error saving recipe:", error);
        alert(`Failed to save recipe: ${error.message}`);
        submitButton.disabled = false;
        submitButton.innerHTML = isEditing ? 
            '<i class="fas fa-save"></i> Update Recipe' : 
            '<i class="fas fa-save"></i> Save Recipe';
    }
}

function postSaveActions(savedRecipe, submitButton) {
    const wasEditing = document.getElementById('recipe-form').dataset.editingId; // Check *before* deleting

    submitButton.disabled = false;
    // After an add or update, the form resets to "Add Recipe" mode.
    submitButton.innerHTML = '<i class="fas fa-save"></i> Save Recipe'; 
    
    if (savedRecipe) {
        document.getElementById('recipe-form').reset();
        // Clear the image file input and its status specifically
        const imageInput = document.getElementById('recipe-image');
        if (imageInput) imageInput.value = ''; 
        const fileUploadStatus = document.getElementById('file-upload-status');
        if (fileUploadStatus) {
            fileUploadStatus.textContent = '';
            fileUploadStatus.className = '';
        }

        if (wasEditing) { // If it was an edit, clear the editing state
            delete document.getElementById('recipe-form').dataset.editingId;
        }
        
        // Remove cancel button if it exists
        const cancelBtn = document.getElementById('cancel-edit-btn');
        if (cancelBtn) cancelBtn.remove();
        
        // Reset form header to "Add New Recipe"
        document.querySelector('#add h2').innerHTML = '<i class="fas fa-plus-circle"></i> Add New Recipe';
        
        loadRecipes(); // Reload recipes to show changes
        switchTab('my-recipes'); // Switch to the recipes list tab
        
        showTemporaryStatusMessage(
            `Recipe "${savedRecipe.name}" ${wasEditing ? 'updated' : 'saved'} successfully!`, 
            'success'
        );
    }
}


// Delete recipe function (called by button)
async function deleteRecipe(id) {
    console.log(id);
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

/* COMMENTED FOR NOW SINCE THERE IS A NEW VIEW RECIPE PAGE (I WON'T DELETE THE OLD ONE BECAUSE IT'S NOT MY CODE) - jason */
// View recipe details (uses local cache) 
// function viewRecipe(id) {
//     const recipe = currentRecipes.find(r => r.id == id);

//     if (recipe) {
//         let ingredientsString = "No ingredients listed.";
//         if (recipe.ingredients && Array.isArray(recipe.ingredients) && recipe.ingredients.length > 0) {
//             ingredientsString = "- " + recipe.ingredients.join('\n- ');
//         } else if (typeof recipe.ingredients === 'string' && recipe.ingredients.trim()) {
//              // Fallback if somehow it's still a string
//              ingredientsString = recipe.ingredients;
//         }

//         alert(`
// --------------------
// RECIPE: ${recipe.name}
// --------------------
// Category: ${recipe.category}
// Time: ${recipe.time} minutes
// Added/Updated: ${recipe.date} ${recipe.author ? '\nAuthor: '+recipe.author : ''}

// INGREDIENTS:
// ${ingredientsString}

// INSTRUCTIONS:
// ${recipe.instructions || 'No instructions provided.'}
// --------------------
//         `);
//     } else {
//         alert('Recipe details not found. The list might be updating, please try again shortly.');
//     }
// }


// Add function to handle editing
function editRecipe(id) {
    const recipe = currentRecipes.find(r => r.id == id);
    if (!recipe) {
        alert('Recipe not found for editing.');
        return;
    }

    switchTab('add');

    document.getElementById('recipe-name').value = recipe.name;
    document.getElementById('recipe-category').value = recipe.category;
    document.getElementById('recipe-time').value = recipe.time;
    document.getElementById('recipe-instructions').value = recipe.instructions;

    // Clear existing ingredients and populate new ones
    ingredients = Array.isArray(recipe.ingredients) ? 
        [...recipe.ingredients] : 
        [];
    renderList();

    document.getElementById('recipe-form').dataset.editingId = id;

    // Update form header and button
    document.querySelector('#add h2').innerHTML = '<i class="fas fa-edit"></i> Edit Recipe';
    document.getElementById('add-recipe-button').textContent = 'Edit Recipe';
    const submitBtn = document.querySelector('#add button[type="submit"]');
    submitBtn.innerHTML = '<i class="fas fa-save"></i> Update Recipe';

    // Add event listener to cancel when switching tabs
    document.getElementById('my-recipes-button').addEventListener('click', cancelEdit);
    document.getElementById('add-recipe-button').addEventListener('click', cancelEdit);
    document.getElementById('recipe-stats-button').addEventListener('click', cancelEdit);
    document.getElementById('share-recipe-button').addEventListener('click', cancelEdit);

    // Add cancel button if missing
    if (!document.getElementById('cancel-edit-btn')) {
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.id = 'cancel-edit-btn';
        cancelBtn.className = 'btn btn-secondary';
        cancelBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
        cancelBtn.onclick = cancelEdit;
        submitBtn.insertAdjacentElement('afterend', cancelBtn);
    }
}

// Cancel edit mode
function cancelEdit() {
    const form = document.getElementById('recipe-form');
    delete form.dataset.editingId;
    form.reset();
    
    // Clear ingredients
    ingredients = [];
    renderList();

    document.querySelector('#add h2').innerHTML = '<i class="fas fa-plus-circle"></i> Add New Recipe';
    document.getElementById('add-recipe-button').textContent = 'Add Recipe';
    document.querySelector('#add button[type="submit"]').innerHTML = '<i class="fas fa-save"></i> Save Recipe';

    // Remove event after being cancelled
    document.getElementById('my-recipes-button').removeEventListener('click', cancelEdit);
    document.getElementById('add-recipe-button').removeEventListener('click', cancelEdit);
    document.getElementById('recipe-stats-button').removeEventListener('click', cancelEdit);
    document.getElementById('share-recipe-button').removeEventListener('click', cancelEdit);

    const cancelBtn = document.getElementById('cancel-edit-btn');
    if (cancelBtn) cancelBtn.remove();
}

// Override default alert
// Override default alert
const originalAlert = window.alert;
window.alert = function(message, buttonsHTML) {
    if (buttonsHTML) {
        const alertBox = document.createElement('div');
        alertBox.className = 'custom-alert';
        alertBox.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
            z-index: 10000;
            max-width: 80%;
            max-height: 80vh;
            overflow: auto;
        `;

        const messageDiv = document.createElement('div');
        messageDiv.style.marginBottom = '15px';
        messageDiv.style.whiteSpace = 'pre-wrap';
        messageDiv.textContent = message;
        alertBox.appendChild(messageDiv);

        const buttonsDiv = document.createElement('div');
        buttonsDiv.style.textAlign = 'right';
        buttonsDiv.innerHTML = buttonsHTML;
        alertBox.appendChild(buttonsDiv);

        document.body.appendChild(alertBox);

        const firstButton = buttonsDiv.querySelector('button');
        if (firstButton) firstButton.focus();
    } else {
        originalAlert(message);
    }
};

// Modify handleFormSubmit to handle update if editing
// Inside handleFormSubmit, before calling addRecipeToServer, add this:
const editingId = document.getElementById('recipe-form').dataset.editingId;
if (editingId) {
    newRecipeData.id = parseInt(editingId, 10);
    // updateRecipeToServer(newRecipeData); // You’d implement this on the backend
} else {
    // continue with addRecipeToServer(newRecipeData);
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

// Add toggle function
function toggleChart(chartType) {
    const state = chartStates[chartType];
    const newState = state === 'all-time' ? 'this-month' : 'all-time';
    
    if (chartType === 'frequency') {
        if (state === 'weekly') {
            document.getElementById('frequency-title').textContent = 'Monthly Cooking Frequency';
        } else {
            document.getElementById('frequency-title').textContent = 'This Week\'s Cooking Frequency';
        }
        
        chartStates[chartType] = state === 'monthly' ? 'weekly' : 'monthly';    
    } else {
        chartStates[chartType] = newState;
    }

    // Update button text
    const button = event.target.closest('button');
    if (button) {
        const toggleText = chartType === 'frequency' ? 
            (chartStates[chartType] === 'monthly' ? 'Show This Week' : 'Show Monthly View') :
            (chartStates[chartType] === 'all-time' ? 'Show This Month' : 'Show All Time');
        button.innerHTML = `<i class="fas fa-exchange-alt"></i> ${toggleText}`;
    }

    // Update charts
    if (chartType === 'top-recipes') {
        const data = chartStates[chartType] === 'all-time' ? 
            LOG_STATS_DATA.top_recipes_data : 
            LOG_STATS_DATA.top_recipes_this_month_data;
        updateTopRecipesChart(data);
    } else if (chartType === 'frequency') {
        if (chartStates[chartType] === 'monthly') {
            updateMonthlyFrequencyChart(LOG_STATS_DATA.monthly_frequency_data);
        } else {
            updateWeeklyFrequencyChart(LOG_STATS_DATA.weekly_frequency_data);
        }
    } else if (chartType === 'top-rated') {
        const data = chartStates[chartType] === 'all-time' ? 
            LOG_STATS_DATA.top_rated_data : 
            LOG_STATS_DATA.top_rated_this_month_data;
        updateTopRatedChart(data);
    }
}

function updateStats() {
    // Use the global LOG_STATS_DATA parsed from the template
    const stats = LOG_STATS_DATA;

    const totalSessionsEl = document.getElementById('total-sessions');
    const mostFrequentRecipeEl = document.getElementById('most-frequent-recipe');
    const mostFrequentCountEl = document.getElementById('most-frequent-count');
    const totalTimeLoggedEl = document.getElementById('total-time-logged');
    const averageRatingEl = document.getElementById('average-rating');

    if (totalSessionsEl) totalSessionsEl.textContent = stats.total_sessions || 0;

    if (mostFrequentRecipeEl) {
        if (stats.most_frequent_recipe && stats.most_frequent_recipe.name && stats.most_frequent_recipe.name !== '-' && stats.most_frequent_recipe.count > 0) {
            mostFrequentRecipeEl.textContent = stats.most_frequent_recipe.name; // Access .name
            if (mostFrequentCountEl) mostFrequentCountEl.textContent = `(${stats.most_frequent_recipe.count} logs)`; // Access .count
        } else {
            mostFrequentRecipeEl.textContent = '-';
            if (mostFrequentCountEl) mostFrequentCountEl.textContent = '';
        }
    }

    if (totalTimeLoggedEl) {
        const totalSeconds = stats.total_time_logged_seconds || 0;
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        totalTimeLoggedEl.textContent = `${hours}h ${minutes}m`;
    }

    if (averageRatingEl) {
        if (stats.average_rating && stats.average_rating > 0) {
            averageRatingEl.textContent = stats.average_rating.toFixed(1) + ' ★';
        } else {
            averageRatingEl.textContent = 'N/A';
        }
    }

    // Update the charts using the data from LOG_STATS_DATA
    if (document.getElementById('top-recipes-chart') && stats.top_recipes_data) {
        updateTopRecipesChart(stats.top_recipes_data);
    }
    if (document.getElementById('top-rated-chart') && LOG_STATS_DATA.top_rated_data) {
        updateTopRatedChart(LOG_STATS_DATA.top_rated_data);
    }
    if (document.getElementById('frequency-chart') && stats.monthly_frequency_data) {
        updateMonthlyFrequencyChart(stats.monthly_frequency_data);
    }
}


// --- Chart Update Functions --- 
function updateCategoryChart(categoryCounts) {
    const ctx = document.getElementById('category-chart')?.getContext('2d');
    if (!ctx) return; // Exit if canvas not found

    const labels = Object.keys(categoryCounts);
    const data = Object.values(categoryCounts);

    const backgroundColors = [
        '#AEDC81', '#92C67F', '#4E944F', '#B7CEB1', '#D4E09B', '#B8E2DC', 
        '#FFE0B2', '#A67B5B', '#F4E2D8', '#A2D2FF', '#9BC995', '#7CA982'
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
function updateTopRecipesChart(topRecipesData) {
    const ctx = document.getElementById('top-recipes-chart')?.getContext('2d');
    if (!ctx) return;

    const labels = topRecipesData.map(item => item.name);
    const data = topRecipesData.map(item => item.count);

    const backgroundColors = ['#AEDC81', '#92C67F', '#4E944F', '#B7CEB1', '#D4E09B']; // Use first 5 theme colors

    if (topRecipesChart) {
        topRecipesChart.destroy(); // Destroy previous chart instance
    }

    topRecipesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Logs',
                data: data,
                backgroundColor: backgroundColors.slice(0, labels.length),
                borderColor: backgroundColors.map(c => c + 'B3'),
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y', // Make it a horizontal bar chart
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { // Note: x-axis for values in horizontal bar chart
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: 'var(--grey)' }, // Ensure integer steps if log counts are low
                    grid: { color: '#eee' }
                },
                y: { // Note: y-axis for labels
                    ticks: { color: 'var(--grey)' },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` Logs: ${context.raw || 0}`;
                        }
                    }
                }
            }
        }
    });
}

function updateMonthlyFrequencyChart(frequencyData) {
    const ctx = document.getElementById('frequency-chart')?.getContext('2d');
    if (!ctx) return;

    const labels = frequencyData.map(item => item.month); // Should be YYYY-MM sorted
    const data = frequencyData.map(item => item.count);

    // Consistent color or cycle through a few
    const barColor = '#AEDC81'; // Primary color

    if (frequencyChart) {
        frequencyChart.destroy(); // Destroy previous instance
    }

    frequencyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sessions Logged',
                data: data,
                backgroundColor: barColor,
                borderColor: barColor + 'B3',
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: 'var(--grey)' }, // Integer steps
                    grid: { color: '#eee' }
                },
                x: {
                    ticks: { color: 'var(--grey)' },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                     callbacks: {
                        title: function(context) {
                             // Format title e.g., "October 2023"
                             const [year, month] = context[0].label.split('-');
                             const date = new Date(year, month - 1); // Month is 0-indexed
                             return date.toLocaleString('default', { month: 'long', year: 'numeric' });
                        },
                        label: function(context) {
                            return ` Sessions: ${context.raw || 0}`;
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
    const backgroundColors = ['#AEDC81', '#92C67F', '#4E944F', '#B7CEB1', '#D4E09B'];

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

function updateWeeklyFrequencyChart(weeklyData) {
    const ctx = document.getElementById('frequency-chart')?.getContext('2d');
    if (!ctx) return;

    const labels = weeklyData.map(item => {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        return days[item.day - 1]; // Adjust for 1-based index from database
    });
    const data = weeklyData.map(item => item.count);

    if (frequencyChart) {
        frequencyChart.destroy();
    }

    frequencyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sessions Logged',
                data: data,
                backgroundColor: '#FF7B54',
                borderColor: '#FF7B54B3',
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: 'var(--grey)' },
                    grid: { color: '#eee' }
                },
                x: {
                    ticks: { color: 'var(--grey)' },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const dayIndex = context[0].label;
                            return ` ${dayIndex}`;
                        }
                    }
                }
            }
        }
    });
}

// Add new chart update functions
function updateTopRatedChart(topRatedData) {
    const ctx = document.getElementById('top-rated-chart')?.getContext('2d');
    if (!ctx) return;

    const labels = topRatedData.map(item => item.name);
    const data = topRatedData.map(item => item.rating);

    if (topRatedChart) {
        topRatedChart.destroy();
    }

    const backgroundColors = ['#AEDC81', '#92C67F', '#4E944F', '#B7CEB1', '#D4E09B']; // Use first 5 theme colors

    topRatedChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Rating',
                data: data,
                backgroundColor: backgroundColors.slice(0, labels.length),
                borderColor: backgroundColors.map(c => c + 'B3'),
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    max: 5,
                    min: 0,
                    ticks: { color: 'var(--grey)' },
                    grid: { color: '#eee' }
                },
                y: {
                    ticks: { color: 'var(--grey)' },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` Rating: ${context.raw?.toFixed(1) || 0} ★`;
                        }
                    }
                }
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

// Share recipe via different platforms -- deleted 

// Shared Recipes Popup Helper Functions
async function fetchSharedRecipes() {
    try {
        const response = await fetch('/api/shared_recipes/my');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching shared recipes:", error);
        return [];
    }
}

function displaySharedRecipes() {
    const sharedRecipesList = document.getElementById('shared-recipes-list');
    const noRecipesMessage = document.getElementById('no-recipes-message');

    // Show loading state
    sharedRecipesList.innerHTML = '<p class="loading-message" style="text-align: center; padding: 20px; color: var(--grey);"><i class="fas fa-spinner fa-spin"></i> Loading shared recipes...</p>';
    noRecipesMessage.style.display = 'none'; // Hide no recipes message while loading

    fetchSharedRecipes().then(shared_recipes => {
        sharedRecipesList.innerHTML = ''; // Clear loading message

        if (shared_recipes.length === 0) {
            noRecipesMessage.style.display = 'block';
            // sharedRecipesList remains empty if no recipes
        } else {
            noRecipesMessage.style.display = 'none';
            
            shared_recipes.forEach(shared_recipe => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'shared-recipe-item';
                
                // Format date for better readability
                const dateShared = new Date(shared_recipe.date_shared);
                const formattedDate = dateShared.toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric'
                });

                itemDiv.innerHTML = `
                    <div class="shared-recipe-icon">
                        <i class="fas fa-utensils"></i>
                    </div>
                    <div class="shared-recipe-details">
                        <h4 class="shared-recipe-name">${shared_recipe.recipe_name}</h4>
                        <p class="shared-recipe-meta">
                            Shared by <strong>${shared_recipe.sharer_name}</strong> on ${formattedDate}
                        </p>
                    </div>
                    <div class="shared-recipe-action">
                        <i class="fas fa-chevron-right"></i>
                    </div>
                `;
                
                itemDiv.addEventListener('click', () => {
                    window.open(`./view_recipe/${shared_recipe.recipe_id}`, '_blank');
                });
                sharedRecipesList.appendChild(itemDiv);
            });
        }
    }).catch(error => {
        console.error('Error fetching shared recipes:', error);
        sharedRecipesList.innerHTML = ''; // Clear loading message on error
        noRecipesMessage.textContent = 'Could not load shared recipes.';
        noRecipesMessage.style.display = 'block';
    });
}


// static/script.js

// ... (Global variables and functions declared above this block) ...
// e.g., topRecipesChart, frequencyChart, currentRecipes,
// fetchRecipes, addRecipeToServer, deleteRecipeFromServer,
// renderRecipeCard, loadRecipes, checkShareDropdown, handleFormSubmit,
// saveRecipe, postSaveActions, deleteRecipe, editRecipe, cancelEdit,
// updateStats, updateTopRecipesChart, updateMonthlyFrequencyChart,
// switchTab, handleFileChange, shareRecipe, closeAlert, etc.


// --- Initial Setup ---
document.addEventListener('DOMContentLoaded', function() {

    // Tab switching
    const tabs = document.querySelectorAll('.tab'); // Get all tab elements
    const tabContents = document.querySelectorAll('.tab-content'); // Get all content elements

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
             console.log('Tab clicked:', tab.getAttribute('data-tab')); // For debugging

            // If the tab is disabled, do nothing
            if (tab.classList.contains('disabled')) return;

            const tabId = tab.getAttribute('data-tab'); // Get the ID of the content to show

            // --- Manage .active class on TABS ---
            tabs.forEach(t => t.classList.remove('active')); // Remove active from ALL tabs
            tab.classList.add('active'); // Add active to the CLICKED tab

            // --- Manage .active class on TAB CONTENTS ---
            tabContents.forEach(content => {
                 content.classList.remove('active'); // Remove active from ALL content divs - HIDES THEM
            });

            // Find the specific content div to activate
            const activeContent = document.getElementById(tabId);
             if (activeContent) {
                 activeContent.classList.add('active'); // Add active ONLY to the target content div - SHOWS IT

                 // Update stats only when that specific tab is viewed
                 if (tabId === 'recipe-stats') { // Ensure this ID matches your HTML
                     console.log('Updating stats for tab:', tabId); // For debugging
                     updateStats(); // Populate stats and render charts
                 }
                  if (tabId === 'add') {
                    const form = document.getElementById('recipe-form');
                    form.reset();
                    delete form.dataset.editingId;

                    if (typeof ingredients !== 'undefined') {
                        ingredients.length = 0;
                        renderList();
                    }

                    document.querySelector('#add h2').innerHTML = '<i class="fas fa-plus-circle"></i> Add New Recipe';
                    document.querySelector('#add button[type="submit"]').innerHTML = '<i class="fas fa-save"></i> Save Recipe';

                    const cancelBtn = document.getElementById('cancel-edit-btn');
                    if (cancelBtn) cancelBtn.remove();
                }
             } else {
                  console.warn(`Tab content with ID "${tabId}" not found.`);
             }
        });
    }); // End of tabs.forEach

    // File upload trigger & feedback
    const fileUploadArea = document.getElementById('file-upload');
    if (fileUploadArea) { // Check if the element exists (it's inside a tab)
        const fileInputElement = document.getElementById('recipe-image');
        if (fileInputElement) { // Also check if input exists
            fileUploadArea.addEventListener('click', () => fileInputElement.click());

            // Drag and Drop Handling
            fileUploadArea.addEventListener('dragover', (event) => {
                event.preventDefault(); // Necessary to allow drop
                fileUploadArea.classList.add('dragging'); // Add class for styling
            });
            fileUploadArea.addEventListener('dragleave', () => {
                 fileUploadArea.classList.remove('dragging'); // Remove class
            });
            fileUploadArea.addEventListener('drop', (event) => {
                event.preventDefault();
                fileUploadArea.classList.remove('dragging');
                if (event.dataTransfer.files.length > 0) {
                    fileInputElement.files = event.dataTransfer.files; // Assign dropped files
                    handleFileChange(fileInputElement); // Update UI
                }
            });
            fileInputElement.addEventListener('change', () => handleFileChange(fileInputElement));
        }
    }

    // Recipe form submission listener
    const recipeForm = document.getElementById('recipe-form');
    if (recipeForm) {
        recipeForm.addEventListener('submit', handleFormSubmit);
        // Note: The cancelEdit function adds/removes a cancel button dynamically
    }

    // Search functionality
    const searchInput = document.getElementById('recipe-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const recipeListContainer = document.getElementById('recipe-list');
            if (!recipeListContainer) return; // Exit if list container not found

            let visibleCount = 0;
            let noResultMessage = recipeListContainer.querySelector('.no-search-results');

             // Remove existing no-results message before filtering
             if (noResultMessage) noResultMessage.remove();

            // Ensure currentRecipes is populated before searching
            if (currentRecipes && currentRecipes.length > 0) {
                currentRecipes.forEach(recipe => {
                    const card = recipeListContainer.querySelector(`.recipe-card[data-id='${recipe.id}']`);
                    if (!card) return; // Skip if card not rendered yet

                    const title = recipe.name ? recipe.name.toLowerCase() : '';
                    const ingredientsText = (Array.isArray(recipe.ingredients) ? recipe.ingredients.join(', ') : '').toLowerCase();
                    const categoryText = recipe.category ? recipe.category.toLowerCase() : '';
                    const isMatch = title.includes(searchTerm) || ingredientsText.includes(searchTerm) || categoryText.includes(searchTerm);

                    card.style.display = isMatch ? '' : 'none';
                    if (isMatch) visibleCount++;
                });
            } else {
                 // Handle case where recipes haven't loaded yet or there are none
                 visibleCount = 0;
            }


            // Add "no results" message if needed AFTER filtering
            if (visibleCount === 0 && currentRecipes && currentRecipes.length > 0 && searchTerm) { // Only show if searching and recipes exist
                noResultMessage = document.createElement('p');
                noResultMessage.className = 'no-search-results';
                noResultMessage.style.cssText = 'grid-column: 1 / -1; text-align: center; color: var(--grey); margin-top: 15px;';
                noResultMessage.textContent = `No recipes found matching "${searchTerm}".`;
                recipeListContainer.appendChild(noResultMessage);
            } else if (visibleCount === 0 && (!currentRecipes || currentRecipes.length === 0) && !searchTerm) {
                 // Handle case where list is empty initially and search is empty (or recipes haven't loaded)
                 // Avoid adding message if loading message is present
                 if (!recipeListContainer.querySelector('p:not(.no-search-results)')) {
                     recipeListContainer.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--grey);">You haven\'t added any recipes yet. Use the "Add Recipe" tab!</p>';
                 }
            }
        }); // End of search input listener
    }

    // Share recipe selection listener & user search input listener for clearing response message
    const shareRecipeSelect = document.getElementById('share-recipe');
    const userSearchInputForShare = document.getElementById("user-search"); // Also known as 'input' below
    const responseMessageDivForShare = document.getElementById('response-message');

    if (shareRecipeSelect) {
        shareRecipeSelect.addEventListener('change', function() {
            displaySharePreview(this.value); // Ensure displaySharePreview exists
            if (responseMessageDivForShare) { // Clear message on recipe change
                responseMessageDivForShare.textContent = '';
                responseMessageDivForShare.style.color = 'var(--grey)'; // Reset color
            }
        });
    }
    if (userSearchInputForShare) {
        userSearchInputForShare.addEventListener('input', function() {
            if (responseMessageDivForShare) { // Clear message on user typing
                responseMessageDivForShare.textContent = '';
                responseMessageDivForShare.style.color = 'var(--grey)';
            }
            // The existing user search suggestion logic will also run
        });
    }


    // Initial load of recipes (for the logged-in user)
    // Check if the recipe list container exists before loading
    if (document.getElementById('recipe-list')) {
        loadRecipes(); // This function updates currentRecipes and renders cards
    }

    // share recipe user search listeners
    const input = document.getElementById("user-search"); // Same as userSearchInputForShare
    const suggestions = document.getElementById("suggestions");
    let debounce;

    if (input && suggestions) { // Check if elements exist
        input.addEventListener("input", () => { // This listener is already clearing responseMessageDivForShare
        const q = input.value.trim();
        clearTimeout(debounce);
        if (q.length < 2) {
            suggestions.innerHTML = "";
            return;
        }
        debounce = setTimeout(() => {
            fetch(`/users/search?q=${encodeURIComponent(q)}`)
            .then(res => res.json())
            .then(usernames => {
                suggestions.innerHTML = "";
                usernames.forEach(username => {
                const li = document.createElement("li");
                li.textContent = username;
                li.addEventListener("click", () => {
                    input.value = username;
                    suggestions.innerHTML = "";
                });
                suggestions.appendChild(li);
                });
            })
            .catch(console.error);
        }, 300);
        });

        document.addEventListener("click", e => {
            if (!input.contains(e.target) && !suggestions.contains(e.target)) { 
                suggestions.innerHTML = "";
            }
        });
    }


    const whitelist_button = document.getElementById("add-to-whitelist-btn");
    // responseMessageDivForShare is already defined
    
    if (whitelist_button && input && responseMessageDivForShare) { 
        whitelist_button.addEventListener("click", () => {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const recipe_id_element = document.getElementById('share-recipe');
            
            // Clear previous message before new attempt
            responseMessageDivForShare.textContent = '';
            responseMessageDivForShare.style.color = 'var(--grey)';


            if (!recipe_id_element) {
                console.error("Share recipe select element not found.");
                responseMessageDivForShare.textContent = "Error: Recipe selection not found.";
                responseMessageDivForShare.style.color = 'var(--danger-text)';
                return;
            }
            const recipe_id = recipe_id_element.value;
            const username = input.value.trim();

            if (!recipe_id) {
                responseMessageDivForShare.textContent = "Please select a recipe to share first.";
                responseMessageDivForShare.style.color = 'var(--warning-text)';
                return;
            }

            if (!username) {
                responseMessageDivForShare.textContent = "Please enter or select a user to share with.";
                responseMessageDivForShare.style.color = 'var(--warning-text)';
                return;
            }
            
            whitelist_button.disabled = true; // Disable button
            whitelist_button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sharing...';


            fetch(`/recipes/${recipe_id}/whitelist`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({ username: username })
            })
            .then(res => {
                if (!res.ok) {
                    return res.json().then(errData => {
                        let err = new Error(errData.error || `HTTP error! status: ${res.status}`);
                        err.data = errData;
                        throw err;
                    });
                }
                return res.json();
            })
            .then(data => {
                responseMessageDivForShare.textContent = data.message;
                responseMessageDivForShare.style.color = 'var(--success-text)';
                input.value = ""; // Clear user search input on success
            })
            .catch(err => {
                console.error("Error adding to whitelist:", err);
                responseMessageDivForShare.textContent = err.message || "Error: Failed to share recipe.";
                responseMessageDivForShare.style.color = 'var(--danger-text)';
            })
            .finally(() => {
                whitelist_button.disabled = false; // Re-enable button
                whitelist_button.innerHTML = 'Add to Whitelist';
            });
        });
    }


    // Mailbox popup initialization
    const mailboxIcon = document.querySelector('.mailbox-icon');
    const mailboxPopup = document.getElementById('mailbox-popup');
    const closePopup = document.getElementById('close-popup');

    if (mailboxIcon && mailboxPopup && closePopup) { 
        mailboxIcon.addEventListener('click', function(e) {
            e.stopPropagation();
            const isVisible = mailboxPopup.style.display === 'block';
            mailboxPopup.style.display = isVisible ? 'none' : 'block';
            if (!isVisible) {
                 displaySharedRecipes();
            }
        });

        closePopup.addEventListener('click', function() {
            mailboxPopup.style.display = 'none';
        });

        document.addEventListener('click', function(e) {
            if (mailboxPopup.style.display === 'block' && // Only act if popup is visible
                !mailboxPopup.contains(e.target) && 
                e.target !== mailboxIcon && 
                !mailboxIcon.contains(e.target)
            ) {
                mailboxPopup.style.display = 'none';
            }
        });
    }
    
    // MISCELLANEOUS STUFF  
    const recipeTimeInput = document.getElementById('recipe-time');
    if (recipeTimeInput) { 
        recipeTimeInput.addEventListener('keypress', function(e) {
            if (!/\d/.test(String.fromCharCode(e.charCode))) {
                e.preventDefault();
            }
        });
    }

}); // End DOMContentLoaded

// --- Ingredient Input ---
let ingredients = [];

function updateHidden() {
  const hiddenInput = document.getElementById('ingredients-hidden');
  hiddenInput.value = ingredients.join(',');
}

function renderList() {
  const listEl = document.getElementById('ingredient-list');
  listEl.innerHTML = '';
  ingredients.forEach((item, idx) => {
    const li = document.createElement('li');
    const span = document.createElement('span');
    span.textContent = item;
    li.appendChild(span);

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.innerHTML = '<i class="fas fa-trash"></i>';
    delBtn.addEventListener('click', () => {
      ingredients.splice(idx, 1);
      renderList();
    });

    li.appendChild(delBtn);
    listEl.appendChild(li);
  });
  updateHidden();
}

document.addEventListener('DOMContentLoaded', () => {
  const ingredientInput   = document.getElementById('ingredient-input');
  const addBtn            = document.getElementById('add-ingredient-btn');

  addBtn.addEventListener('click', () => {
    const val = ingredientInput.value.trim();
    if (!val) return;
    ingredients.push(val);
    ingredientInput.value = '';
    ingredientInput.focus();
    renderList();
  });
});