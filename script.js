// static/script.js

// Global variables for charts
let categoryChart = null;
let timeChart = null;
let currentRecipes = []; // Cache recipes locally for search/share dropdowns

// --- API Helper Functions ---

async function fetchRecipes() {
    try {
        const response = await fetch('/api/recipes');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const recipes = await response.json();
        currentRecipes = recipes; // Update local cache
        return recipes;
    } catch (error) {
        console.error("Error fetching recipes:", error);
        alert("Failed to load recipes from the server.");
        currentRecipes = []; // Clear cache on error
        return []; // Return empty array on error
    }
}

async function addRecipeToServer(recipeData) {
    try {
        const response = await fetch('/api/recipes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(recipeData),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.error || 'Unknown error'}`);
        }
        const newRecipe = await response.json();
        // Add to local cache immediately for responsiveness (optional but good UX)
        currentRecipes.unshift(newRecipe); // Add to beginning assuming sorted by new
        return newRecipe;
    } catch (error) {
        console.error("Error adding recipe:", error);
        alert(`Failed to save recipe: ${error.message}`);
        return null;
    }
}

async function deleteRecipeFromServer(recipeId) {
    try {
        const response = await fetch(`/api/recipes/${recipeId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.error || 'Unknown error'}`);
        }
        // Remove from local cache
        currentRecipes = currentRecipes.filter(r => r.id !== recipeId);
        return true; // Indicate success
    } catch (error) {
        console.error(`Error deleting recipe ${recipeId}:`, error);
        alert(`Failed to delete recipe: ${error.message}`);
        return false; // Indicate failure
    }
}


// --- UI Rendering and Logic (Mostly unchanged, but uses fetched data) ---

// Function to render a single recipe card
function renderRecipeCard(recipe) {
    const recipeCard = document.createElement('div');
    recipeCard.className = 'recipe-card';
    recipeCard.dataset.id = recipe.id;

    const ingredientsPreview = (recipe.ingredients || []).slice(0, 4).join(', ') + ((recipe.ingredients || []).length > 4 ? '...' : '');
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
                <strong>Ingredients:</strong> ${ingredientsPreview}
            </p>
            <div class="recipe-actions">
                <button class="btn btn-secondary" onclick="viewRecipe(${recipe.id})">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn btn-danger" onclick="deleteRecipe(${recipe.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `;
    return recipeCard;
}

// Load recipes into the UI and Share dropdown
async function loadRecipes() {
    const recipeList = document.getElementById('recipe-list');
    const shareRecipeSelect = document.getElementById('share-recipe');

    recipeList.innerHTML = '<p style="grid-column: 1/-1; text-align: center;">Loading recipes...</p>'; // Show loading indicator
    shareRecipeSelect.innerHTML = '<option value="">Loading...</option>';

    const recipes = await fetchRecipes(); // Fetch fresh data

    // Clear existing content
    recipeList.innerHTML = '';
    shareRecipeSelect.innerHTML = '<option value="">Select a recipe</option>';

    if (recipes.length === 0) {
        recipeList.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--grey);">No recipes yet. Add your first recipe using the "Add Recipe" tab!</p>';
    } else {
        // Note: Recipes are now sorted by ID (desc) on the server
        recipes.forEach(recipe => {
            const recipeCard = renderRecipeCard(recipe);
            recipeList.appendChild(recipeCard);

            const option = document.createElement('option');
            option.value = recipe.id;
            option.textContent = recipe.name;
            shareRecipeSelect.appendChild(option);
        });
    }

    // Update stats and check share dropdown validity
    updateStats(); // Uses the global `currentRecipes` cache
    checkShareDropdown();
}

function checkShareDropdown() {
    const shareRecipeSelect = document.getElementById('share-recipe');
    const currentShareId = shareRecipeSelect.value;
    if (currentShareId && !currentRecipes.some(r => r.id == currentShareId)) {
         document.getElementById('share-preview').style.display = 'none';
         shareRecipeSelect.value = '';
    } else if (currentShareId) {
        // Refresh preview if still valid
         displaySharePreview(currentShareId);
    } else {
        document.getElementById('share-preview').style.display = 'none';
    }
}

// --- Event Handlers ---

// Handle form submission
async function handleFormSubmit(event) {
    event.preventDefault();

    const name = document.getElementById('recipe-name').value.trim();
    const category = document.getElementById('recipe-category').value;
    const timeInput = document.getElementById('recipe-time').value;
    const ingredients = document.getElementById('recipe-ingredients').value.trim();
    const instructions = document.getElementById('recipe-instructions').value.trim();
    const imageInput = document.getElementById('recipe-image');

    if (!name || !category || !timeInput || !ingredients || !instructions) {
         alert('Please fill in all required fields.');
         return;
    }
    const time = parseInt(timeInput, 10);
     if (isNaN(time) || time <= 0) {
         alert('Please enter a valid positive number for preparation time.');
         return;
     }

    const newRecipeData = {
        name,
        category,
        time,
        ingredients: ingredients.split(',').map(i => i.trim()).filter(i => i),
        instructions,
        date: new Date().toISOString(),
        image: null
    };

    // Disable button during processing
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Saving...';

    // Handle image upload (async)
    if (imageInput.files.length > 0) {
        const reader = new FileReader();
        reader.onload = async function(event) {
            newRecipeData.image = event.target.result;
            const savedRecipe = await addRecipeToServer(newRecipeData);
            postSaveActions(savedRecipe, submitButton);
        };
        reader.onerror = function() {
            console.error("Error reading file");
            alert("Error reading image file. Recipe will be saved without image.");
            // Try saving without image
            addRecipeToServer(newRecipeData).then(savedRecipe => {
                 postSaveActions(savedRecipe, submitButton);
            });
        };
        reader.readAsDataURL(imageInput.files[0]);
    } else {
        // Save without image
        const savedRecipe = await addRecipeToServer(newRecipeData);
        postSaveActions(savedRecipe, submitButton);
    }
}

// Actions to take after trying to save a recipe
function postSaveActions(savedRecipe, submitButton) {
     // Re-enable button
    submitButton.disabled = false;
    submitButton.textContent = 'Save Recipe';

    if (savedRecipe) {
        // Reset form & file input display
        document.getElementById('recipe-form').reset();
        const fileUploadStatus = document.getElementById('file-upload-status');
        document.getElementById('recipe-image').value = ''; // Clear file input
        fileUploadStatus.textContent = '';
        fileUploadStatus.className = '';

        // Reload recipe list and switch tab
        loadRecipes(); // Reloads everything including stats and dropdown
        switchTab('recipes');
        alert('Recipe saved successfully!');
    } else {
        // Error already handled in addRecipeToServer, alert shown there
    }
}


// Delete recipe function (called by button)
async function deleteRecipe(id) {
    if (confirm('Are you sure you want to delete this recipe? This cannot be undone.')) {
        const success = await deleteRecipeFromServer(id);
        if (success) {
             // Remove the card directly from the DOM for instant feedback
            const cardToRemove = document.querySelector(`.recipe-card[data-id='${id}']`);
            if (cardToRemove) {
                cardToRemove.remove();
            }
            // Reload lists/stats to ensure consistency
            loadRecipes(); // This re-fetches, updates stats, and share dropdown
             // alert('Recipe deleted.'); // Optional confirmation
        }
        // Error alert handled in deleteRecipeFromServer
    }
}

// View recipe details (uses local cache)
function viewRecipe(id) {
    const recipe = currentRecipes.find(r => r.id == id); // Find in local cache

    if (recipe) {
        alert(`
Recipe: ${recipe.name}
Category: ${recipe.category}
Time: ${recipe.time} minutes

Ingredients:
- ${(recipe.ingredients || []).join('\n- ')}

Instructions:
${recipe.instructions}
        `);
    } else {
        // This might happen if cache is stale, could add a fetch here
        alert('Recipe details not found. Try reloading the page.');
    }
}

// Display share preview (uses local cache)
function displaySharePreview(recipeId) {
     const sharePreview = document.getElementById('share-preview');
     const recipe = currentRecipes.find(r => r.id == recipeId); // Find in local cache

     if (recipe) {
         sharePreview.style.display = 'block';
         document.getElementById('share-title').textContent = recipe.name;
         document.getElementById('share-category').innerHTML = `<i class="fas fa-tag category-icon"></i> ${recipe.category}`;
         document.getElementById('share-time').innerHTML = `<i class="fas fa-clock time-icon"></i> ${recipe.time} mins`;

         const shareImage = document.getElementById('share-image');
         shareImage.style.backgroundImage = recipe.image
             ? `url(${recipe.image})`
             : 'linear-gradient(135deg, var(--primary-color), var(--secondary-color))';
     } else {
         sharePreview.style.display = 'none';
     }
}


// --- Stats and Charts (uses local cache) ---

function updateStats() {
    const recipes = currentRecipes; // Use the cached data
    const totalRecipes = recipes.length;

    document.getElementById('total-recipes').textContent = totalRecipes;

    if (totalRecipes > 0) {
        const categoryCounts = recipes.reduce((acc, recipe) => {
            acc[recipe.category] = (acc[recipe.category] || 0) + 1;
            return acc;
        }, {});
        const mostCommonCategory = Object.keys(categoryCounts).reduce((a, b) =>
            categoryCounts[a] > categoryCounts[b] ? a : b, Object.keys(categoryCounts)[0] || '-'
        );
         document.getElementById('most-cooked').textContent = mostCommonCategory || '-';


        const totalTime = recipes.reduce((sum, recipe) => sum + (recipe.time || 0), 0); // Ensure time exists
        const avgTime = totalTime / totalRecipes;
        document.getElementById('total-time').textContent = totalTime;
        document.getElementById('avg-time').textContent = avgTime.toFixed(1);

        updateCategoryChart(categoryCounts);
        updateTimeChart(recipes);

    } else {
        document.getElementById('most-cooked').textContent = '-';
        document.getElementById('total-time').textContent = '0';
        document.getElementById('avg-time').textContent = '0';
        updateCategoryChart({});
        updateTimeChart([]);
    }
}

// --- Chart Update Functions (Unchanged - Required Chart.js) ---
// updateCategoryChart, updateTimeChart functions remain the same as before...
// ... (Keep your existing chart update functions here) ...
function updateCategoryChart(categoryCounts) {
    const ctx = document.getElementById('category-chart').getContext('2d');
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
    const ctx = document.getElementById('time-chart').getContext('2d');
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
     if (targetTab && !targetTab.classList.contains('active')) { // Avoid unnecessary clicks
         targetTab.click();
     }
}

// Handle file input change for immediate feedback
function handleFileChange(fileInput) {
    const fileUploadStatus = document.getElementById('file-upload-status');
    if (fileInput.files.length > 0) {
        const fileName = fileInput.files[0].name;
        // Basic validation (optional: check file type/size here)
        fileUploadStatus.innerHTML = `<i class="fas fa-check-circle success"></i> File selected: ${fileName}`;
        fileUploadStatus.className = 'success';
    } else {
        fileUploadStatus.textContent = '';
        fileUploadStatus.className = '';
    }
}

// Share recipe via different platforms (Unchanged - Doesn't depend on storage method)
function shareRecipe(platform) {
    const recipeId = document.getElementById('share-recipe').value;
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
    const shareSubject = `My Recipe: ${recipe.name}`;
    const shareBody = `${shareText}\n\nIngredients:\n- ${(recipe.ingredients || []).join('\n- ')}\n\nInstructions:\n${recipe.instructions}\n\nShared from my Recipe Tracker: ${appUrl}`;
    let shareUrl = '';

    switch (platform) {
        case 'facebook':
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(appUrl)}"e=${encodeURIComponent(shareText)}`;
            break;
        case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(appUrl)}`;
            break;
        case 'whatsapp':
            shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText + ' ' + appUrl)}`;
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
            const tabId = tab.getAttribute('data-tab');
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            tabContents.forEach(c => c.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            if (tabId === 'stats') {
                updateStats(); // Update stats when tab is viewed
            }
        });
    });

    // File upload trigger & feedback
    const fileUploadArea = document.getElementById('file-upload');
    const fileInputElement = document.getElementById('recipe-image');
    fileUploadArea.addEventListener('click', () => fileInputElement.click());
    fileInputElement.addEventListener('change', () => handleFileChange(fileInputElement));

    // Recipe form submission listener
    const recipeForm = document.getElementById('recipe-form');
    recipeForm.addEventListener('submit', handleFormSubmit);

    // Search functionality (uses local cache `currentRecipes`)
    const searchInput = document.getElementById('recipe-search');
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        const recipeCards = document.querySelectorAll('#recipe-list .recipe-card');
        let visibleCount = 0;

        // Filter based on the cached recipe data, not just the DOM
        currentRecipes.forEach(recipe => {
            const card = document.querySelector(`.recipe-card[data-id='${recipe.id}']`);
            if (!card) return; // Skip if card not rendered yet or removed

            const title = recipe.name.toLowerCase();
            const ingredientsText = (recipe.ingredients || []).join(', ').toLowerCase();
            const categoryText = recipe.category.toLowerCase();
            const isMatch = title.includes(searchTerm) || ingredientsText.includes(searchTerm) || categoryText.includes(searchTerm);

            if (isMatch) {
                card.style.display = '';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        // Handle "no results" message
        const recipeListContainer = document.getElementById('recipe-list');
        let noResultMessage = recipeListContainer.querySelector('.no-search-results');
        if (visibleCount === 0 && searchTerm !== '' && currentRecipes.length > 0) {
             if (!noResultMessage) {
                noResultMessage = document.createElement('p');
                noResultMessage.className = 'no-search-results';
                noResultMessage.style.cssText = 'grid-column: 1 / -1; text-align: center; color: var(--grey); margin-top: 15px;';
                // Insert after search bar, or append if layout simple
                 recipeListContainer.insertBefore(noResultMessage, recipeListContainer.firstChild.nextSibling); // Attempt placement
            }
            noResultMessage.textContent = `No recipes found matching "${searchTerm}".`;
        } else if (noResultMessage) {
            noResultMessage.remove();
        } else if (visibleCount === 0 && currentRecipes.length === 0 && !recipeListContainer.querySelector('p')) {
             // Handle case where list is empty initially and search is cleared
             recipeListContainer.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--grey);">No recipes yet. Add your first recipe using the "Add Recipe" tab!</p>';
        }
    });

    // Share recipe selection listener
    const shareRecipeSelect = document.getElementById('share-recipe');
    shareRecipeSelect.addEventListener('change', function() {
        displaySharePreview(this.value); // Uses the display function
    });

    // Initial load of recipes
    loadRecipes();

}); // End DOMContentLoaded