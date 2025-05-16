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
    console.log("fetchRecipes: Initiating fetch for /api/recipes");
    try {
        const response = await fetch('/api/recipes');
        console.log(`fetchRecipes: Response status: ${response.status}`);
        if (!response.ok) {
            const errorText = await response.text(); // Get raw error text
            console.error(`fetchRecipes: HTTP error! Status: ${response.status}, Body: ${errorText}`);
            if (response.status === 401) {
                 alert("Your session may have expired. Please log in again.");
                 window.location.href = '/auth/login'; // Corrected login URL
            }
            // Try to parse as JSON for more structured error, but fallback to text
            let errorDetail = errorText;
            try {
                const errorJson = JSON.parse(errorText);
                errorDetail = errorJson.error || errorJson.details || errorText;
            } catch (e) { /* ignore if not json */ }
            throw new Error(`Server error: ${response.status} - ${errorDetail}`);
        }
        const recipes = await response.json();
        console.log("fetchRecipes: Successfully fetched and parsed recipes. Count:", recipes.length);
        currentRecipes = recipes; // Update global cache
        return recipes;
    } catch (error) {
        console.error("fetchRecipes: CATCH BLOCK - Error fetching recipes:", error.message, error.stack);
        // alert(`Failed to load your recipes. ${error.message}. Check console for details.`);
        currentRecipes = []; // Reset global cache on error
        return []; // Return empty array so UI can show "no recipes" or "error"
    }
}

async function fetchApi(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            let errorMessage = 'Unknown error';
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.message || JSON.stringify(errorData);
            } catch (e) {
                errorMessage = await response.text() || `Status ${response.status}`;
            }
            console.error(`fetchApi: HTTP error! Status: ${response.status}, URL: ${url}, Message: ${errorMessage}`);
            if (response.status === 401 && (options.method !== 'GET' || url !== '/api/recipes')) { // Avoid double alert from fetchRecipes
                 alert("Your session may have expired or you are unauthorized. Please log in again.");
                 window.location.href = '/auth/login'; // Corrected login URL
            }
            throw new Error(`HTTP error! Status: ${response.status} - ${errorMessage}`);
        }
        
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            return await response.json();
        }
        return await response.text();
    } catch (error) {
        console.error(`API Error (${options.method || 'GET'} ${url}):`, error);
        throw error; // Rethrow for specific handling
    }
}

function showTemporaryStatusMessage(message, type = 'info', duration = 3000) {
    const statusDiv = document.createElement('div');
    statusDiv.className = `alert alert-${type}`;
    statusDiv.textContent = message;
    
    statusDiv.style.position = 'fixed';
    statusDiv.style.top = '20px';
    statusDiv.style.left = '50%';
    statusDiv.style.transform = 'translateX(-50%)';
    statusDiv.style.zIndex = '1050';
    statusDiv.style.padding = '10px 20px'; 
    statusDiv.style.borderRadius = '5px'; 
    statusDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)'; 
    statusDiv.style.opacity = '1';
    statusDiv.style.transition = 'opacity 0.5s ease-out';

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
        statusDiv.style.opacity = '0'; 
        setTimeout(() => {
            if (statusDiv.parentNode) {
                statusDiv.parentNode.removeChild(statusDiv);
            }
        }, 500); 
    }, duration);
}


function copyRecipeLink() { // This function seems unused in current home.html, but kept if needed elsewhere
    const linkInput = document.getElementById('recipe-share-link');
    if (!linkInput || !linkInput.value) {
        showTemporaryStatusMessage('No recipe link available to copy.', 'warning');
        return;
    }

    linkInput.focus(); 
    linkInput.select(); 
    linkInput.setSelectionRange(0, 99999); 

    try {
        if (document.execCommand('copy')) {
            showTemporaryStatusMessage('Link copied to clipboard!', 'success');
        } else {
            throw new Error('execCommand returned false');
        }
    } catch (err) {
        console.warn('execCommand copy failed, attempting Clipboard API fallback.', err);
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(linkInput.value)
                .then(() => {
                    showTemporaryStatusMessage('Link copied to clipboard!', 'success');
                })
                .catch(clipboardErr => {
                    console.error('Clipboard API fallback failed:', clipboardErr);
                    showTemporaryStatusMessage('Failed to copy link automatically.', 'danger');
                    alert('Could not copy link automatically. Please select the link text and copy it manually (Ctrl+C or Cmd+C).');
                });
        } else {
            console.error('Clipboard API not available.');
            showTemporaryStatusMessage('Failed to copy link. Browser does not support clipboard operations.', 'danger');
            alert('Could not copy link automatically. Please select the link text and copy it manually (Ctrl+C or Cmd+C).');
        }
    } finally {
        setTimeout(() => {
            window.getSelection()?.removeAllRanges();
        }, 100);
    }
}


async function addRecipeToServer(recipeData) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        console.error("CSRF token not found in meta tag!");
        alert("Action failed: Security token missing. Please refresh the page.");
        return null;
    }

    try {
        const newRecipe = await fetchApi('/api/recipes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(recipeData),
        });
        currentRecipes.unshift(newRecipe);
        return newRecipe;
    } catch (error) {
        alert(`Failed to save recipe: ${error.message.replace("HTTP error! Status: \\d+ - ", "")}`);
        return null;
    }
}

async function deleteRecipeFromServer(recipeId) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
     if (!csrfToken) {
        console.error("CSRF token not found in meta tag!");
        alert("Action failed: Security token missing. Please refresh the page.");
        return false;
    }

    try {
        await fetchApi(`/api/recipes/${recipeId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        currentRecipes = currentRecipes.filter(r => r.id !== recipeId);
        return true;
    }
    catch (error) {
        alert(`Failed to delete recipe: ${error.message.replace("HTTP error! Status: \\d+ - ", "")}`);
        return false;
    }
}

// --- UI Rendering ---

function renderRecipeCard(recipe) {
    try {
        const recipeCard = document.createElement('div');
        recipeCard.className = 'recipe-card';
        recipeCard.dataset.id = recipe.id;

        const ingredients = recipe.ingredients || [];
        const ingredientsPreview = (Array.isArray(ingredients) ? ingredients : [])
            .slice(0, 4).join(', ') + (ingredients.length > 4 ? '...' : '');
        
        const imageStyle = recipe.image
            ? `background-image: url(${encodeURI(recipe.image)});`
            : 'background-image: linear-gradient(135deg, var(--primary-color), var(--secondary-color));';

        const recipeName = recipe.name || 'Untitled Recipe';
        const recipeCategory = recipe.category || 'Uncategorized';
        const recipeTime = recipe.time || 0;
        const recipeUserId = recipe.user_id;


        recipeCard.innerHTML = `
            <div class="recipe-img" style="${imageStyle}"></div>
            <div class="recipe-info">
                <h3 class="recipe-title">${recipeName}</h3>
                <div class="recipe-meta">
                    <span><i class="fas fa-tag category-icon"></i> ${recipeCategory}</span>
                    <span><i class="fas fa-clock time-icon"></i> ${recipeTime} mins</span>
                </div>
                <p class="recipe-ingredients-preview">
                    <strong>Ingredients:</strong> ${ingredientsPreview || 'No ingredients listed'}
                </p>
                <div class="recipe-actions">
                    <a href="/view_recipe/${recipe.id}" class="btn btn-secondary btn-sm">
                        <i class="fas fa-eye"></i> View
                    </a>
                    ${typeof CURRENT_USER_ID !== 'undefined' && recipeUserId === CURRENT_USER_ID ? `
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
    } catch (e) {
        console.error("Error in renderRecipeCard for recipe:", recipe, e);
        const errorCard = document.createElement('div');
        errorCard.className = 'recipe-card';
        errorCard.innerHTML = `<div class="recipe-info"><h3 class="recipe-title" style="color:red;">Error displaying recipe</h3><p>${(recipe && recipe.name) || (recipe && 'ID: '+recipe.id) || 'Unknown Recipe'}</p></div>`;
        return errorCard;
    }
}

async function loadRecipes() {
    console.log("loadRecipes: Function CALLED.");
    const recipeList = document.getElementById('recipe-list');
    const shareRecipeSelect = document.getElementById('share-recipe');

    if (!recipeList) {
        console.error("loadRecipes: CRITICAL - recipe-list element NOT FOUND in DOM! Aborting.");
        return;
    }
    console.log("loadRecipes: recipe-list element found.");

    recipeList.innerHTML = '<p style="grid-column: 1/-1; text-align: center;"><i class="fas fa-spinner fa-spin"></i> Loading your recipes...</p>';
    console.log("loadRecipes: 'Loading...' message displayed.");

    if (shareRecipeSelect) {
        shareRecipeSelect.innerHTML = '<option value="">Loading...</option>';
        shareRecipeSelect.disabled = true;
    }
    const sharePreview = document.getElementById('share-preview');
    if (sharePreview) {
        sharePreview.style.display = 'none';
    }


    let recipes = [];
    try {
        console.log("loadRecipes: Awaiting fetchRecipes()...");
        recipes = await fetchRecipes(); 
        console.log("loadRecipes: fetchRecipes() completed. Recipes count:", recipes.length);
    } catch (error) { 
        console.error("loadRecipes: CATCH BLOCK - Error awaiting fetchRecipes():", error);
        recipeList.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--danger-text);">An error occurred while loading recipes. Please check the console and try refreshing.</p>';
        if (shareRecipeSelect) shareRecipeSelect.disabled = true;
        if (typeof updateStats === "function") updateStats(); else console.warn("loadRecipes: updateStats function not available.");
        if (typeof checkShareDropdown === "function") checkShareDropdown(); else console.warn("loadRecipes: checkShareDropdown function not available.");
        return; 
    }

    console.log("loadRecipes: Clearing 'Loading...' message.");
    recipeList.innerHTML = ''; 

    if (shareRecipeSelect) {
        shareRecipeSelect.innerHTML = '<option value="">Select a recipe to share</option>';
        if (recipes.length > 0) {
            let hasOwnedRecipes = false;
            recipes.forEach(recipe => {
                if (typeof CURRENT_USER_ID !== 'undefined' && recipe.user_id === CURRENT_USER_ID) {
                    const option = document.createElement('option');
                    option.value = recipe.id;
                    option.textContent = recipe.name;
                    shareRecipeSelect.appendChild(option);
                    hasOwnedRecipes = true;
                }
            });
            shareRecipeSelect.disabled = !hasOwnedRecipes;
        } else {
            shareRecipeSelect.disabled = true;
        }
    }

    if (recipes.length === 0) {
        console.log("loadRecipes: No recipes to display.");
        if (!recipeList.textContent.toLowerCase().includes("error")) {
             recipeList.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--grey);">You haven\'t added any recipes yet. Use the "Add Recipe" tab!</p>';
        }
    } else {
        console.log("loadRecipes: Rendering recipe cards...");
        recipes.forEach(recipe => {
            try {
                const recipeCard = renderRecipeCard(recipe); 
                recipeList.appendChild(recipeCard);
            } catch (renderError) {
                console.error("loadRecipes: Error rendering recipe card for recipe:", recipe, renderError);
            }
        });
        console.log("loadRecipes: Finished rendering cards.");
    }

    console.log("loadRecipes: Calling updateStats().");
    if (typeof updateStats === "function" && typeof LOG_STATS_DATA !== 'undefined') {
        updateStats();
    } else {
        console.warn("loadRecipes: updateStats function or LOG_STATS_DATA not available.");
    }

    console.log("loadRecipes: Calling checkShareDropdown().");
    if (typeof checkShareDropdown === "function") {
        checkShareDropdown();
    } else {
        console.warn("loadRecipes: checkShareDropdown function not available.");
    }
    console.log("loadRecipes: Function COMPLETED.");
}

function checkShareDropdown() {
    const shareRecipeSelect = document.getElementById('share-recipe');
    if (!shareRecipeSelect) return;

    const currentShareId = shareRecipeSelect.value;
    const sharePreview = document.getElementById('share-preview');

    const recipeExists = currentRecipes.some(r => r.id == currentShareId);

    if (currentShareId && !recipeExists) {
         if (sharePreview) sharePreview.style.display = 'none';
         shareRecipeSelect.value = ''; 
         shareRecipeSelect.disabled = shareRecipeSelect.options.length <= 1 || !currentRecipes.some(r => typeof CURRENT_USER_ID !== 'undefined' && r.user_id === CURRENT_USER_ID);
    } else if (currentShareId && sharePreview && recipeExists) {
         displaySharePreview(currentShareId);
    } else if (sharePreview) { 
        sharePreview.style.display = 'none';
    }
    if (!currentRecipes.some(r => typeof CURRENT_USER_ID !== 'undefined' && r.user_id === CURRENT_USER_ID)) {
        shareRecipeSelect.disabled = true;
    }
}

// --- Event Handlers ---

async function handleFormSubmit(event) {
    event.preventDefault();
    console.log("handleFormSubmit: Form submission initiated.");

    const name = document.getElementById('recipe-name').value.trim();
    const category = document.getElementById('recipe-category').value;
    const timeInput = document.getElementById('recipe-time').value;
    const ingredientsText = document.getElementById('recipe-ingredients').value.trim();
    const instructions = document.getElementById('recipe-instructions').value.trim();
    const imageInput = document.getElementById('recipe-image');

    if (!name || !category || !timeInput || !ingredientsText || !instructions) {
        alert('Please fill in all required fields: Name, Category, Time, Ingredients, and Instructions.');
        console.warn("handleFormSubmit: Validation failed - missing fields.");
        return;
    }
    const time = parseInt(timeInput, 10);
    if (isNaN(time) || time <= 0) {
        alert('Please enter a valid time (must be a number greater than 0).');
        console.warn("handleFormSubmit: Validation failed - invalid time.");
        return;
    }

    const ingredientsList = ingredientsText.split(/[\n,]+/).map(i => i.trim()).filter(i => i);
    if (ingredientsList.length === 0) {
        alert('Please list at least one ingredient.');
        console.warn("handleFormSubmit: Validation failed - no ingredients.");
        return;
    }

    const form = document.getElementById('recipe-form');
    const isEditing = form.dataset.editingId;
    console.log(`handleFormSubmit: Mode: ${isEditing ? 'Editing recipe ID ' + isEditing : 'Adding new recipe'}`);

    const recipeData = {
        name,
        category,
        time,
        ingredients: ingredientsList,
        instructions,
    };

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    if (imageInput.files.length > 0) {
        console.log("handleFormSubmit: Processing new image.");
        const imagePromise = new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                recipeData.image = e.target.result; 
                console.log("handleFormSubmit: Image read successfully.");
                resolve(); 
            };
            reader.onerror = function(error) {
                console.error("handleFormSubmit: Error reading image file.", error);
                alert("Error reading image file. The recipe will be saved without this new image.");
                resolve(); 
            };
            reader.readAsDataURL(imageInput.files[0]);
        });

        try {
            await imagePromise;
        } catch (error) { 
            alert(`Failed to process image: ${error.message}. Proceeding without image update.`);
            console.error("handleFormSubmit: Image promise rejected (unexpected).", error);
        }
    } else {
        console.log("handleFormSubmit: No new image selected.");
    }
    
    await saveRecipe(recipeData, isEditing, submitButton);
    console.log("handleFormSubmit: saveRecipe call completed.");
}

async function saveRecipe(recipeData, isEditing, submitButton) {
    let savedRecipe;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        console.error("saveRecipe: CSRF token not found!");
        alert("Action failed: Security token missing. Please refresh the page.");
        postSaveActions(null, submitButton, isEditing); 
        return;
    }

    try {
        if (isEditing) {
            console.log(`saveRecipe: Updating recipe ID ${isEditing}`);
            savedRecipe = await fetchApi(`/api/recipes/${isEditing}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(recipeData)
            });
            const index = currentRecipes.findIndex(r => r.id == isEditing); 
            if (index !== -1) {
                currentRecipes[index] = savedRecipe;
            }
            console.log(`saveRecipe: Recipe ID ${isEditing} updated.`);
        } else {
            console.log("saveRecipe: Adding new recipe.");
            savedRecipe = await addRecipeToServer(recipeData); 
            console.log("saveRecipe: New recipe added.", savedRecipe);
        }
        
        postSaveActions(savedRecipe, submitButton, isEditing);

    } catch (error) {
        console.error("saveRecipe: Error saving recipe:", error);
        postSaveActions(null, submitButton, isEditing); 
    }
}

function postSaveActions(savedRecipe, submitButton, wasEditing) {
    submitButton.disabled = false;
    submitButton.innerHTML = wasEditing ? 
        '<i class="fas fa-save"></i> Update Recipe' : 
        '<i class="fas fa-save"></i> Save Recipe';
    
    if (savedRecipe) {
        console.log(`postSaveActions: Recipe "${savedRecipe.name}" ${wasEditing ? 'updated' : 'saved'} successfully.`);
        document.getElementById('recipe-form').reset();
        const imageInput = document.getElementById('recipe-image');
        if (imageInput) imageInput.value = ''; 
        const fileUploadStatus = document.getElementById('file-upload-status');
        if (fileUploadStatus) {
            fileUploadStatus.textContent = '';
            fileUploadStatus.className = '';
        }

        if (wasEditing) { 
            delete document.getElementById('recipe-form').dataset.editingId;
        }
        
        const cancelBtn = document.getElementById('cancel-edit-btn');
        if (cancelBtn) cancelBtn.remove();
        
        document.querySelector('#add h2').innerHTML = '<i class="fas fa-plus-circle"></i> Add New Recipe';
        submitButton.innerHTML = '<i class="fas fa-save"></i> Save Recipe';
        
        loadRecipes(); 
        switchTab('my-recipes');
        
        showTemporaryStatusMessage(
            `Recipe "${savedRecipe.name}" ${wasEditing ? 'updated' : 'saved'} successfully!`, 
            'success'
        );
    } else {
        console.warn("postSaveActions: saveRecipe resulted in no savedRecipe object (likely an error).");
    }
}


async function deleteRecipe(id) {
    console.log(`deleteRecipe: Attempting to delete recipe ID ${id}`);
    const recipe = currentRecipes.find(r => r.id === id); 
    const recipeName = recipe ? `"${recipe.name}"` : "this recipe";

    if (confirm(`Are you sure you want to delete ${recipeName}? This cannot be undone.`)) {
        const success = await deleteRecipeFromServer(id);
        if (success) {
            console.log(`deleteRecipe: Recipe ID ${id} successfully deleted from server.`);
            loadRecipes(); 
            showTemporaryStatusMessage(`Recipe ${recipeName} deleted successfully.`, 'info');
        } else {
            console.warn(`deleteRecipe: Failed to delete recipe ID ${id} from server.`);
        }
    } else {
        console.log(`deleteRecipe: Deletion of recipe ID ${id} cancelled by user.`);
    }
}

function editRecipe(id) {
    console.log(`editRecipe: Editing recipe ID ${id}`);
    const recipe = currentRecipes.find(r => r.id == id); 
    if (!recipe) {
        alert('Recipe not found for editing.');
        console.warn(`editRecipe: Recipe ID ${id} not found in currentRecipes.`);
        return;
    }

    document.getElementById('recipe-name').value = recipe.name;
    document.getElementById('recipe-category').value = recipe.category;
    document.getElementById('recipe-time').value = recipe.time;
    document.getElementById('recipe-ingredients').value = Array.isArray(recipe.ingredients) ? 
        recipe.ingredients.join('\n') : (recipe.ingredients || '');
    document.getElementById('recipe-instructions').value = recipe.instructions || '';
    
    const imageInput = document.getElementById('recipe-image');
    if (imageInput) imageInput.value = ''; 
    const fileUploadStatus = document.getElementById('file-upload-status');
    if (fileUploadStatus) {
        fileUploadStatus.textContent = recipe.image ? `Current image retained. Choose a new file to replace.` : 'No image. Choose a file to upload.';
        fileUploadStatus.className = recipe.image ? 'info' : '';
    }


    document.getElementById('recipe-form').dataset.editingId = id;

    document.querySelector('#add h2').innerHTML = '<i class="fas fa-edit"></i> Edit Recipe';
    document.querySelector('#add button[type="submit"]').innerHTML = '<i class="fas fa-save"></i> Update Recipe';

    if (!document.getElementById('cancel-edit-btn')) {
        const submitBtn = document.querySelector('#add button[type="submit"]');
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.id = 'cancel-edit-btn';
        cancelBtn.className = 'btn btn-secondary';
        cancelBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
        cancelBtn.onclick = cancelEdit;
        submitBtn.insertAdjacentElement('afterend', cancelBtn);
    }

    switchTab('add');
    document.getElementById('recipe-name').focus(); 
}

function cancelEdit() {
    console.log("cancelEdit: Edit mode cancelled.");
    const form = document.getElementById('recipe-form');
    delete form.dataset.editingId;
    form.reset();

    document.querySelector('#add h2').innerHTML = '<i class="fas fa-plus-circle"></i> Add New Recipe';
    document.querySelector('#add button[type="submit"]').innerHTML = '<i class="fas fa-save"></i> Save Recipe';

    const cancelBtn = document.getElementById('cancel-edit-btn');
    if (cancelBtn) cancelBtn.remove();

    const fileUploadStatus = document.getElementById('file-upload-status');
    if (fileUploadStatus) {
        fileUploadStatus.textContent = '';
        fileUploadStatus.className = '';
    }
    const imageInput = document.getElementById('recipe-image');
    if (imageInput) imageInput.value = '';
    switchTab('my-recipes'); 
}

const originalAlert = window.alert;
window.alert = function(message, buttonsHTML) { 
    if (buttonsHTML && typeof buttonsHTML === 'string') { 
        console.warn("Custom alert with HTML buttons called. Ensure HTML is safe.");
        const alertOverlay = document.createElement('div');
        alertOverlay.className = 'custom-alert-overlay';
        alertOverlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(0,0,0,0.5); z-index: 9999; display: flex;
            align-items: center; justify-content: center;
        `;

        const alertBox = document.createElement('div');
        alertBox.className = 'custom-alert-box'; 
        alertBox.style.cssText = `
            background: white; padding: 25px; border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); z-index: 10000;
            max-width: 90%; width: 400px; text-align: center;
            color: #333;
        `;

        const messageDiv = document.createElement('div');
        messageDiv.style.marginBottom = '20px';
        messageDiv.style.whiteSpace = 'pre-wrap';
        messageDiv.style.fontSize = '1.1em';
        messageDiv.textContent = message;
        alertBox.appendChild(messageDiv);

        const buttonsDiv = document.createElement('div');
        buttonsDiv.style.textAlign = 'right'; 
        buttonsDiv.innerHTML = buttonsHTML; 
        alertBox.appendChild(buttonsDiv);
        
        alertOverlay.appendChild(alertBox);
        document.body.appendChild(alertOverlay);

        buttonsDiv.querySelectorAll('button').forEach(button => {
            if (!button.onclick) { 
                button.addEventListener('click', () => closeCustomAlert(alertOverlay));
            }
        });
        alertOverlay.addEventListener('click', (e) => {
            if (e.target === alertOverlay) { 
                closeCustomAlert(alertOverlay);
            }
        });


        const firstButton = buttonsDiv.querySelector('button');
        if (firstButton) firstButton.focus();
    } else {
        console.log("Using original alert for message:", message)
        originalAlert(message);
    }
};

function closeCustomAlert(alertOverlay) {
    if (alertOverlay && alertOverlay.parentNode) {
        alertOverlay.parentNode.removeChild(alertOverlay);
    }
}


function displaySharePreview(recipeId) {
    const sharePreview = document.getElementById('share-preview');
    const userSearchInput = document.getElementById('user-search');
    const addToWhitelistBtn = document.getElementById('add-to-whitelist-btn');
    const responseMessage = document.getElementById('response-message');

    if (!sharePreview) {
        console.warn("displaySharePreview: share-preview element not found.");
        return;
    }

    if (!recipeId) { 
        sharePreview.style.display = 'none';
        if (userSearchInput) userSearchInput.disabled = true;
        if (addToWhitelistBtn) addToWhitelistBtn.disabled = true;
        if (responseMessage) responseMessage.textContent = '';
        return;
    }

    const recipe = currentRecipes.find(r => r.id == recipeId); 

    if (recipe) {
        const isOwner = typeof CURRENT_USER_ID !== 'undefined' && recipe.user_id === CURRENT_USER_ID;

        sharePreview.style.display = 'block';
        document.getElementById('share-title').textContent = recipe.name;
        document.getElementById('share-category').innerHTML = `<i class="fas fa-tag category-icon"></i> ${recipe.category}`;
        document.getElementById('share-time').innerHTML = `<i class="fas fa-clock time-icon"></i> ${recipe.time} mins`;

        const shareImage = document.getElementById('share-image');
        if (shareImage) {
            shareImage.style.backgroundImage = recipe.image
                ? `url(${encodeURI(recipe.image)})`
                : 'linear-gradient(135deg, var(--primary-color), var(--secondary-color))';
        }
        
        if (userSearchInput) userSearchInput.disabled = !isOwner;
        if (addToWhitelistBtn) addToWhitelistBtn.disabled = !isOwner;
        if (responseMessage) {
            responseMessage.textContent = isOwner ? '' : 'You can only manage sharing for your own recipes.';
            responseMessage.className = isOwner ? '' : 'info'; // Use 'info' class for non-owner message
        }

    } else {
        console.warn(`displaySharePreview: Recipe ID ${recipeId} not found in currentRecipes.`);
        sharePreview.style.display = 'none';
        if (userSearchInput) userSearchInput.disabled = true;
        if (addToWhitelistBtn) addToWhitelistBtn.disabled = true;
        if (responseMessage) {
            responseMessage.textContent = 'Selected recipe not found.';
            responseMessage.className = 'error';
        }
    }
}


// --- Stats and Charts ---

function toggleChart(event, chartType) { 
    const state = chartStates[chartType];
    let newState;
    
    const titleElement = document.getElementById(`${chartType === 'frequency' ? 'frequency' : chartType}-title`);
    const button = event.currentTarget; 

    if (chartType === 'frequency') {
        newState = state === 'monthly' ? 'weekly' : 'monthly';
        if (titleElement) titleElement.textContent = newState === 'weekly' ? 'This Week\'s Cooking Frequency' : 'Monthly Cooking Frequency';
    } else {
        newState = state === 'all-time' ? 'this-month' : 'all-time';
    }
    chartStates[chartType] = newState;

    if (button) {
        const toggleText = chartType === 'frequency' ? 
            (newState === 'monthly' ? 'Show This Week' : 'Show Monthly View') :
            (newState === 'all-time' ? 'Show This Month' : 'Show All Time');
        button.innerHTML = `<i class="fas fa-exchange-alt"></i> ${toggleText}`;
    }

    if (typeof LOG_STATS_DATA === 'undefined') {
        console.warn("toggleChart: LOG_STATS_DATA is undefined. Cannot update charts.");
        return;
    }

    if (chartType === 'top-recipes') {
        const data = newState === 'all-time' ? 
            LOG_STATS_DATA.top_recipes_data : 
            LOG_STATS_DATA.top_recipes_this_month_data;
        updateTopRecipesChart(data);
    } else if (chartType === 'frequency') {
        if (newState === 'monthly') {
            updateMonthlyFrequencyChart(LOG_STATS_DATA.monthly_frequency_data);
        } else {
            updateWeeklyFrequencyChart(LOG_STATS_DATA.weekly_frequency_data);
        }
    } else if (chartType === 'top-rated') {
        const data = newState === 'all-time' ? 
            LOG_STATS_DATA.top_rated_data : 
            LOG_STATS_DATA.top_rated_this_month_data;
        updateTopRatedChart(data);
    }
}

function updateStats() {
    if (typeof LOG_STATS_DATA === 'undefined') {
        console.warn("updateStats: LOG_STATS_DATA is not defined. Cannot update stats.");
        const fieldsToClear = ['total-sessions', 'most-frequent-recipe', 'most-frequent-count', 'total-time-logged', 'average-rating'];
        fieldsToClear.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = id.includes('count') ? '' : (id.includes('rating') ? 'N/A' : (id.includes('time') ? '0h 0m' : (id.includes('recipe') ? '-' : '0')));

        });
        if (topRecipesChart) updateTopRecipesChart([]);
        if (frequencyChart) updateMonthlyFrequencyChart([]); 
        if (topRatedChart) updateTopRatedChart([]);
        return;
    }
    console.log("updateStats: Updating statistics display using LOG_STATS_DATA:", LOG_STATS_DATA);
    const stats = LOG_STATS_DATA;

    const totalSessionsEl = document.getElementById('total-sessions');
    const mostFrequentRecipeEl = document.getElementById('most-frequent-recipe');
    const mostFrequentCountEl = document.getElementById('most-frequent-count');
    const totalTimeLoggedEl = document.getElementById('total-time-logged');
    const averageRatingEl = document.getElementById('average-rating');

    if (totalSessionsEl) totalSessionsEl.textContent = stats.total_sessions || 0;

    if (mostFrequentRecipeEl) {
        if (stats.most_frequent_recipe && stats.most_frequent_recipe.name && stats.most_frequent_recipe.name !== '-' && stats.most_frequent_recipe.count > 0) {
            mostFrequentRecipeEl.textContent = stats.most_frequent_recipe.name;
            if (mostFrequentCountEl) mostFrequentCountEl.textContent = `(${stats.most_frequent_recipe.count} logs)`;
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

    if (document.getElementById('top-recipes-chart') && stats.top_recipes_data) {
        updateTopRecipesChart(stats.top_recipes_data);
        chartStates['top-recipes'] = 'all-time'; 
    }
    if (document.getElementById('top-rated-chart') && stats.top_rated_data) {
        updateTopRatedChart(stats.top_rated_data);
        chartStates['top-rated'] = 'all-time'; 
    }
    if (document.getElementById('frequency-chart') && stats.monthly_frequency_data) {
        updateMonthlyFrequencyChart(stats.monthly_frequency_data);
        chartStates['frequency'] = 'monthly'; 
        const freqTitle = document.getElementById('frequency-title');
        if (freqTitle) freqTitle.textContent = 'Monthly Cooking Frequency';
        
        // Ensure toggleChart function can find the button via its parent event listener.
        // The button itself is in home.html:
        // <button class="chart-toggle-btn btn btn-sm" onclick="toggleChart(event, 'frequency')">
        // So, it should be fine.
    }
}


// --- Chart Update Functions --- 
let categoryChart = null; 
let timeChart = null; 

function updateCategoryChart(categoryCounts) { 
    const ctx = document.getElementById('category-chart')?.getContext('2d');
    if (!ctx) return; 

    const labels = Object.keys(categoryCounts);
    const data = Object.values(categoryCounts);
    const backgroundColors = ['#FF7B54', '#FFB26B', '#FFD56F', '#939B62', '#4E8C87', '#6B5B95', '#F7CAC9', '#92A8D1', '#F4A261', '#E76F51', '#2A9D8F', '#264653'];

    if (categoryChart) categoryChart.destroy();
    categoryChart = new Chart(ctx, { /* ... chart config ... */ });
}

function updateTopRecipesChart(topRecipesData) {
    const ctx = document.getElementById('top-recipes-chart')?.getContext('2d');
    if (!ctx) return;
    if (!topRecipesData) topRecipesData = []; 

    const labels = topRecipesData.map(item => item.name);
    const data = topRecipesData.map(item => item.count);
    const backgroundColors = ['#FF7B54', '#FFB26B', '#FFD56F', '#939B62', '#4E8C87'];

    if (topRecipesChart) topRecipesChart.destroy();
    topRecipesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Logs', data: data,
                backgroundColor: backgroundColors.slice(0, labels.length),
                borderColor: backgroundColors.map(c => c + 'B3').slice(0, labels.length),
                borderWidth: 1, borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            scales: {
                x: { beginAtZero: true, ticks: { stepSize: 1, color: 'var(--grey)' }, grid: { color: 'var(--chart-grid-color, #eee)' } },
                y: { ticks: { color: 'var(--grey)' }, grid: { display: false } }
            },
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` Logs: ${ctx.raw || 0}` } } }
        }
    });
}

function updateMonthlyFrequencyChart(frequencyData) {
    const ctx = document.getElementById('frequency-chart')?.getContext('2d');
    if (!ctx) return;
    if (!frequencyData) frequencyData = [];

    const labels = frequencyData.map(item => item.month); 
    const data = frequencyData.map(item => item.count);
    const barColor = '#FF7B54'; 

    if (frequencyChart) frequencyChart.destroy(); 
    frequencyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sessions Logged', data: data,
                backgroundColor: barColor, borderColor: barColor + 'B3',
                borderWidth: 1, borderRadius: 4,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, color: 'var(--grey)' }, grid: { color: 'var(--chart-grid-color, #eee)' } },
                x: { ticks: { color: 'var(--grey)' }, grid: { display: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                     callbacks: {
                        title: (context) => {
                             if (!context[0] || !context[0].label) return '';
                             const [year, month] = context[0].label.split('-');
                             const date = new Date(year, parseInt(month, 10) - 1); 
                             return date.toLocaleString('default', { month: 'long', year: 'numeric' });
                        },
                        label: ctx => ` Sessions: ${ctx.raw || 0}`
                    }
                }
            }
        }
    });
}

function updateTimeChart(recipes) { 
    const ctx = document.getElementById('time-chart')?.getContext('2d');
    if (!ctx) return; 
    if (!recipes) recipes = [];
}

function updateWeeklyFrequencyChart(weeklyData) {
    const ctx = document.getElementById('frequency-chart')?.getContext('2d');
    if (!ctx) return;
    if (!weeklyData) weeklyData = [];

    const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const labels = weeklyData.map(item => daysOfWeek[item.day]); 
    const data = weeklyData.map(item => item.count);

    if (frequencyChart) frequencyChart.destroy();
    frequencyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sessions Logged', data: data,
                backgroundColor: '#FF7B54', borderColor: '#FF7B54B3',
                borderWidth: 1, borderRadius: 4,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, color: 'var(--grey)' }, grid: { color: 'var(--chart-grid-color, #eee)' } },
                x: { ticks: { color: 'var(--grey)' }, grid: { display: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { title: ctx => `${ctx[0]?.label || ''}`, label: ctx_1 => ` Sessions: ${ctx_1.raw || 0}` } }
            }
        }
    });
}

function updateTopRatedChart(topRatedData) {
    const ctx = document.getElementById('top-rated-chart')?.getContext('2d');
    if (!ctx) return;
    if (!topRatedData) topRatedData = [];

    const labels = topRatedData.map(item => item.name);
    const data = topRatedData.map(item => item.rating);
    const backgroundColors = ['#FF7B54', '#FFB26B', '#FFD56F', '#939B62', '#4E8C87']; 

    if (topRatedChart) topRatedChart.destroy();
    topRatedChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Rating', data: data,
                backgroundColor: backgroundColors.slice(0, labels.length),
                borderColor: backgroundColors.map(c => c + 'B3').slice(0, labels.length),
                borderWidth: 1, borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            scales: {
                x: { max: 5, min: 0, ticks: { color: 'var(--grey)', stepSize: 1 }, grid: { color: 'var(--chart-grid-color, #eee)' } },
                y: { ticks: { color: 'var(--grey)' }, grid: { display: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: ctx => ` Rating: ${(ctx.raw || 0).toFixed(1)} ★` } }
            }
        }
    });
}

// --- Utility and Event Listeners Setup ---

function switchTab(tabId) {
    console.log(`switchTab: Switching to tab "${tabId}"`);
    const targetTabButton = document.querySelector(`.tab[data-tab="${tabId}"]`);
    const targetTabContent = document.getElementById(tabId);
    
    if (targetTabButton && targetTabContent) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        targetTabButton.classList.add('active');
        targetTabContent.classList.add('active');
        if (tabId === 'recipe-stats' && typeof LOG_STATS_DATA !== 'undefined') {
            console.log("switchTab: Stats tab activated, calling updateStats().");
            updateStats();
        }
    } else {
        console.warn(`switchTab: Could not switch to tab. Button or content not found for tabId "${tabId}"`);
    }
}

function handleFileChange(fileInput) {
    const fileUploadStatus = document.getElementById('file-upload-status');
    if (!fileUploadStatus) return; 

    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const fileName = file.name;
        const fileSize = (file.size / 1024 / 1024).toFixed(2); 
        
        if (fileSize > 5) { 
            fileUploadStatus.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: var(--danger-text);"></i> File too large: ${fileName} (${fileSize}MB). Max 5MB.`;
            fileUploadStatus.className = 'error';
            fileInput.value = ''; 
            return;
        }
        if (!file.type.startsWith('image/')) {
             fileUploadStatus.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: var(--danger-text);"></i> Invalid file type: ${fileName}. Please upload an image.`;
             fileUploadStatus.className = 'error';
             fileInput.value = ''; 
             return;
        }
        fileUploadStatus.innerHTML = `<i class="fas fa-check-circle" style="color: var(--success-text);"></i> File selected: ${fileName} (${fileSize}MB)`;
        fileUploadStatus.className = 'success';
    } else {
        const form = document.getElementById('recipe-form');
        if (form && form.dataset.editingId) {
            const recipe = currentRecipes.find(r => r.id == form.dataset.editingId);
            fileUploadStatus.textContent = recipe && recipe.image ? `Current image retained. Choose a new file to replace.` : 'No image. Choose a file to upload.';
            fileUploadStatus.className = recipe && recipe.image ? 'info' : '';
        } else {
            fileUploadStatus.textContent = '';
            fileUploadStatus.className = '';
        }
    }
}

function shareRecipe(platform) {
    const shareRecipeSelect = document.getElementById('share-recipe');
    if (!shareRecipeSelect) return;

    const recipeId = shareRecipeSelect.value;
    if (!recipeId) {
        alert('Please select a recipe to share first.');
        return;
    }
    const recipe = currentRecipes.find(r => r.id == recipeId);
    if (!recipe) {
        alert('Selected recipe details not found.');
        return;
    }

    const shareText = `Check out my recipe for "${recipe.name}"! Prep time: ${recipe.time} mins. Category: ${recipe.category}.`;
    const appUrl = window.location.origin; 
    const recipePageUrl = `${appUrl}/view_recipe/${recipe.id}`; 

    const shareSubject = `My KitchenLog Recipe: ${recipe.name}`;
    let ingredientsList = Array.isArray(recipe.ingredients) ? recipe.ingredients.join('\n- ') : recipe.ingredients;
    const shareBody = `${shareText}\n\nIngredients:\n- ${ingredientsList}\n\nInstructions:\n${recipe.instructions || 'Not specified.'}\n\nView on KitchenLog: ${recipePageUrl}`;
    let shareUrl = '';

    switch (platform) {
        case 'facebook':
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(recipePageUrl)}"e=${encodeURIComponent(shareText)}`;
            break;
        case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText + " " + recipePageUrl)}`;
            break;
        case 'whatsapp':
            shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText + ' View on KitchenLog: ' + recipePageUrl)}`;
            break;
        case 'email':
            shareUrl = `mailto:?subject=${encodeURIComponent(shareSubject)}&body=${encodeURIComponent(shareBody)}`;
            break;
        case 'copy': 
            copyRecipeLinkToClipboard(recipePageUrl, recipe.name);
            return; 
        default: return;
    }
    if (shareUrl) {
        window.open(shareUrl, '_blank', 'noopener,noreferrer,width=600,height=400');
    }
}

function copyRecipeLinkToClipboard(url, recipeName) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url)
            .then(() => {
                showTemporaryStatusMessage(`Link to "${recipeName}" copied to clipboard!`, 'success');
            })
            .catch(err => {
                console.error('Failed to copy link using Clipboard API:', err);
                showTemporaryStatusMessage('Failed to copy link automatically.', 'danger');
                alert(`Could not copy link automatically. Link for "${recipeName}": ${url}. Please copy manually.`);
            });
    } else { 
        const textArea = document.createElement("textarea");
        textArea.value = url;
        textArea.style.position = "fixed"; 
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
            showTemporaryStatusMessage(`Link to "${recipeName}" copied! (Legacy method)`, 'success');
        } catch (err) {
            console.error('Failed to copy link using execCommand:', err);
            showTemporaryStatusMessage('Failed to copy link.', 'danger');
            alert(`Could not copy link. Link for "${recipeName}": ${url}. Please copy manually.`);
        }
        document.body.removeChild(textArea);
    }
}


async function fetchSharedRecipes() { 
    try {
        console.log("fetchSharedRecipes: Fetching /api/shared_recipes/my");
        const sharedData = await fetchApi('/api/shared_recipes/my');
        console.log("fetchSharedRecipes: Received data:", sharedData);
        return sharedData;
    } catch (error) {
        const sharedRecipesList = document.getElementById('shared-recipes-list');
        const noRecipesMessage = document.getElementById('no-recipes-message');
        if (sharedRecipesList) sharedRecipesList.innerHTML = ''; 
        if (noRecipesMessage) {
            noRecipesMessage.textContent = 'Could not load shared recipes. Please try again later.';
            noRecipesMessage.style.display = 'block';
        }
        return []; 
    }
}

function displaySharedRecipes() {
    const sharedRecipesList = document.getElementById('shared-recipes-list');
    const noRecipesMessage = document.getElementById('no-recipes-message');

    if (!sharedRecipesList || !noRecipesMessage) {
        console.error("displaySharedRecipes: Critical elements not found (shared-recipes-list or no-recipes-message).");
        return;
    }

    sharedRecipesList.innerHTML = '<p class="loading-message" style="text-align: center; padding: 20px; color: var(--grey);"><i class="fas fa-spinner fa-spin"></i> Loading shared recipes...</p>';
    noRecipesMessage.style.display = 'none'; 

    fetchSharedRecipes().then(shared_recipes => {
        sharedRecipesList.innerHTML = ''; 

        if (!Array.isArray(shared_recipes)) {
            console.error("displaySharedRecipes: fetchSharedRecipes did not return an array.", shared_recipes);
            noRecipesMessage.textContent = 'Error: Invalid data received for shared recipes.';
            noRecipesMessage.style.display = 'block';
            return;
        }

        if (shared_recipes.length === 0 && !noRecipesMessage.textContent.toLowerCase().includes("could not load")) { 
            noRecipesMessage.textContent = "You currently have no recipes shared with you.";
            noRecipesMessage.style.display = 'block';
        } else if (shared_recipes.length > 0) {
            noRecipesMessage.style.display = 'none';
            shared_recipes.forEach(shared_recipe => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'shared-recipe-item';
                const dateShared = new Date(shared_recipe.date_shared);
                const formattedDate = dateShared.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });

                // Determine profile image or default icon
                let sharerImageHTML;
                if (shared_recipe.sharer_profile_image_url) {
                    sharerImageHTML = `<img src="${shared_recipe.sharer_profile_image_url}" alt="${shared_recipe.sharer_name}" class="shared-recipe-sharer-avatar">`;
                } else {
                    sharerImageHTML = `<div class="shared-recipe-sharer-avatar default"><i class="fas fa-user"></i></div>`;
                }

                itemDiv.innerHTML = `
                    <div class="shared-recipe-icon">
                        ${sharerImageHTML}
                    </div>
                    <div class="shared-recipe-details">
                        <h4 class="shared-recipe-name">${shared_recipe.recipe_name}</h4>
                        <p class="shared-recipe-meta">Shared by <strong>${shared_recipe.sharer_name}</strong> on ${formattedDate}</p>
                    </div>
                    <div class="shared-recipe-action"><i class="fas fa-chevron-right"></i></div>`;
                
                itemDiv.addEventListener('click', () => {
                    // Link to view_recipe page (already correct)
                    window.location.href = `/view_recipe/${shared_recipe.recipe_id}`;
                });
                sharedRecipesList.appendChild(itemDiv);
            });
        } else if (shared_recipes.length === 0 && noRecipesMessage.textContent.toLowerCase().includes("could not load")) {
            noRecipesMessage.style.display = 'block';
        }
    }).catch(error => { 
        console.error('displaySharedRecipes: CATCH BLOCK - Error processing shared recipes:', error);
        sharedRecipesList.innerHTML = ''; 
        noRecipesMessage.textContent = 'An unexpected error occurred while displaying shared recipes.';
        noRecipesMessage.style.display = 'block';
    });
}


// --- Whitelist Management Functions (New) ---
async function searchUsers(query) {
    const suggestionsList = document.getElementById('suggestions');
    if (query.length < 1) { 
        suggestionsList.innerHTML = '';
        suggestionsList.style.display = 'none';
        return;
    }
    try {
        const users = await fetchApi(`/users/search?q=${encodeURIComponent(query)}`);
        suggestionsList.innerHTML = '';
        if (users.length > 0) {
            users.forEach(username => {
                const li = document.createElement('li');
                li.textContent = username;
                li.addEventListener('click', () => {
                    document.getElementById('user-search').value = username;
                    suggestionsList.style.display = 'none';
                    suggestionsList.innerHTML = '';
                });
                suggestionsList.appendChild(li);
            });
            suggestionsList.style.display = 'block';
        } else {
            suggestionsList.innerHTML = '<li>No users found</li>'; // Indicate no users
            suggestionsList.style.display = 'block';
        }
    } catch (error) {
        console.error("Error searching users:", error);
        suggestionsList.innerHTML = '<li>Error loading suggestions</li>';
        suggestionsList.style.display = 'block';
    }
}

async function handleAddToWhitelist() {
    const recipeId = document.getElementById('share-recipe').value;
    const usernameToWhitelist = document.getElementById('user-search').value.trim();
    const responseMessageDiv = document.getElementById('response-message');
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    if (!recipeId) {
        responseMessageDiv.textContent = 'Please select a recipe first.';
        responseMessageDiv.className = 'error';
        return;
    }
    if (!usernameToWhitelist) {
        responseMessageDiv.textContent = 'Please enter or select a username to add.';
        responseMessageDiv.className = 'error';
        return;
    }
    if (!csrfToken) {
        responseMessageDiv.textContent = 'Security token missing. Please refresh.';
        responseMessageDiv.className = 'error';
        console.error("CSRF token not found for whitelist action.");
        return;
    }

    responseMessageDiv.textContent = 'Processing...';
    responseMessageDiv.className = 'info';

    try {
        const response = await fetchApi(`/recipes/${recipeId}/whitelist`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'Accept': 'application/json'
            },
            body: JSON.stringify({ username: usernameToWhitelist })
        });

        responseMessageDiv.textContent = response.message || 'Action completed.';
        responseMessageDiv.className = 'success';
        document.getElementById('user-search').value = ''; 
        // Optionally, if you store whitelist on recipe object in currentRecipes, update it
        // and re-render something, or fetch shared users for this recipe.
        // For now, a success message is sufficient.
    } catch (error) {
        console.error("Error adding to whitelist:", error);
        const coreErrorMessage = error.message.includes("HTTP error!") ?
            error.message.substring(error.message.indexOf("- ") + 2) :
            error.message;
        responseMessageDiv.textContent = `Error: ${coreErrorMessage}`;
        responseMessageDiv.className = 'error';
    }
}


// --- Initial Setup ---
document.addEventListener('DOMContentLoaded', function() {
    console.log("script.js: DOMContentLoaded event FIRED.");

    if (typeof CURRENT_USER_ID === 'undefined') console.warn("script.js DOMContentLoaded: CURRENT_USER_ID is undefined.");
    if (typeof LOG_STATS_DATA === 'undefined') console.warn("script.js DOMContentLoaded: LOG_STATS_DATA is undefined.");

    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    console.log(`script.js DOMContentLoaded: Found ${tabs.length} tabs and ${tabContents.length} tab contents.`);

    tabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.getAttribute('data-tab')));
    });
    if (!document.querySelector('.tab.active') && tabs.length > 0) {
        const initialTab = window.location.hash.substring(1) || tabs[0].getAttribute('data-tab');
        if (document.getElementById(initialTab) && document.querySelector(`.tab[data-tab="${initialTab}"]`)) {
            switchTab(initialTab);
        } else {
            switchTab(tabs[0].getAttribute('data-tab'));
        }
    }


    const recipeForm = document.getElementById('recipe-form');
    if (recipeForm) recipeForm.addEventListener('submit', handleFormSubmit);

    const recipeImageInput = document.getElementById('recipe-image');
    if (recipeImageInput) recipeImageInput.addEventListener('change', () => handleFileChange(recipeImageInput));
    
    const shareRecipeSelect = document.getElementById('share-recipe');
    if (shareRecipeSelect) {
        shareRecipeSelect.addEventListener('change', function() { displaySharePreview(this.value); });
        // Initial call to displaySharePreview will be handled after loadRecipes completes and populates currentRecipes
    }
    
    // Chart toggle buttons have onclick attributes in HTML, e.g., onclick="toggleChart(event, 'top-recipes')"

    if (document.getElementById('recipe-list')) {
        console.log("script.js DOMContentLoaded: recipe-list found, calling loadRecipes().");
        loadRecipes().then(() => {
            // After recipes are loaded, then call displaySharePreview for the initially selected recipe (if any)
            if (shareRecipeSelect) {
                displaySharePreview(shareRecipeSelect.value);
            }
        });
    } else {
        console.warn("script.js DOMContentLoaded: recipe-list element NOT found. Recipes will not be loaded for this page.");
    }

    const mailboxIcon = document.querySelector('.mailbox-icon'); // Changed from #mailbox-icon if it's a class
    const mailboxPopup = document.getElementById('mailbox-popup');
    const closePopup = document.getElementById('close-popup');

    if (mailboxIcon && mailboxPopup && closePopup) { 
        mailboxIcon.addEventListener('click', function(e) {
            e.stopPropagation(); 
            const isVisible = mailboxPopup.style.display === 'block';
            mailboxPopup.style.display = isVisible ? 'none' : 'block';
            if (!isVisible) displaySharedRecipes();
        });
        closePopup.addEventListener('click', () => mailboxPopup.style.display = 'none');
        document.addEventListener('click', function(e) {
            if (mailboxPopup.style.display === 'block' && !mailboxPopup.contains(e.target) && e.target !== mailboxIcon && !mailboxIcon.contains(e.target)) {
                mailboxPopup.style.display = 'none';
            }
        });
    } else {
        console.warn("Mailbox elements not found. Mailbox feature may not work.");
    }
    
    const recipeTimeInput = document.getElementById('recipe-time');
    if (recipeTimeInput) { 
        recipeTimeInput.addEventListener('keypress', function(e) {
            if (!/\d/.test(String.fromCharCode(e.which || e.keyCode))) e.preventDefault();
        });
        recipeTimeInput.addEventListener('input', e => e.target.value = e.target.value.replace(/[^0-9]/g, ''));
    }

    // Whitelist User Search Event Listener (New)
    const userSearchInput = document.getElementById('user-search');
    if (userSearchInput) {
        let searchTimeout;
        userSearchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchUsers(userSearchInput.value.trim());
            }, 300); 
        });
        document.addEventListener('click', function(e) {
            const suggestionsList = document.getElementById('suggestions');
            if (suggestionsList && !userSearchInput.contains(e.target) && !suggestionsList.contains(e.target)) {
                suggestionsList.style.display = 'none';
            }
        });
    }

    // Add to Whitelist Button Event Listener (New)
    const addToWhitelistBtn = document.getElementById('add-to-whitelist-btn');
    if (addToWhitelistBtn) {
        addToWhitelistBtn.addEventListener('click', handleAddToWhitelist);
    }
     // Initial state for whitelist controls based on whether a recipe is selected
    if (shareRecipeSelect && userSearchInput && addToWhitelistBtn) {
        if (!shareRecipeSelect.value) {
            userSearchInput.disabled = true;
            addToWhitelistBtn.disabled = true;
        }
    }
    
    const style = document.createElement('style');
    style.textContent = `
        #response-message.success { color: var(--success-text); margin-top: 10px; font-weight: bold; }
        #response-message.error { color: var(--danger-text); margin-top: 10px; font-weight: bold; }
        #response-message.info { color: var(--info-text); margin-top: 10px; }
        #suggestions {
            position: absolute;
            background-color: white;
            border: 1px solid #ddd;
            z-index: 100;
            max-height: 150px;
            overflow-y: auto;
            /* Adjust width relative to its container or the input field */
            left: 0; /* Or align with input */
            right: 0; /* Or align with input */
            margin-top: 0; /* Position directly below input */
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        /* Ensure the parent of #user-search and #suggestions has position: relative; if needed */
        .form-group /* or a specific wrapper for #user-search */ {
            position: relative; 
        }
        #suggestions li {
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
        }
        #suggestions li:last-child {
            border-bottom: none;
        }
        #suggestions li:hover {
            background-color: #f5f5f5;
        }
    `;
    document.head.appendChild(style);

    console.log("script.js: DOMContentLoaded setup COMPLETED.");
});