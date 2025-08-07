// News Portals JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    
    // Search functionality
    const searchInput = document.getElementById('news-portals-search');
    const searchForm = searchInput?.closest('form');
    let searchTimeout;
    
    if (searchInput) {
        // Real-time search with debouncing
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            // Debounce the search to avoid too many requests
            searchTimeout = setTimeout(() => {
                if (query.length >= 2 || query.length === 0) {
                    performSearch(query);
                }
            }, 300);
        });
        
        // Handle form submission
        if (searchForm) {
            searchForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const query = searchInput.value.trim();
                performSearch(query);
            });
        }
        
        // Handle keyboard navigation
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                this.value = '';
                performSearch('');
                this.blur();
            }
        });
        
        // Add clear button if search has value
        if (searchInput.value) {
            addClearButton();
        }
        
        // Show/hide clear button based on input value
        searchInput.addEventListener('input', function() {
            if (this.value) {
                addClearButton();
            } else {
                removeClearButton();
            }
        });
        
        // Focus search input on page load if there's a search query
        if (searchInput.value) {
            searchInput.focus();
            searchInput.setSelectionRange(searchInput.value.length, searchInput.value.length);
        }
    }
    
    // Function to perform search
    function performSearch(query) {
        const currentUrl = new URL(window.location);
        
        if (query) {
            currentUrl.searchParams.set('search', query);
        } else {
            currentUrl.searchParams.delete('search');
        }
        
        // Reset to first page when searching
        currentUrl.searchParams.delete('page');
        
        // Navigate to the search results
        window.location.href = currentUrl.toString();
    }
    
    // Function to add clear button
    function addClearButton() {
        if (document.getElementById('clear-search-btn')) return;
        
        const clearSearchButton = document.createElement('button');
        clearSearchButton.type = 'button';
        clearSearchButton.id = 'clear-search-btn';
        clearSearchButton.className = 'absolute inset-y-0 right-8 flex items-center pr-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300';
        clearSearchButton.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        `;
        
        clearSearchButton.addEventListener('click', function() {
            searchInput.value = '';
            performSearch('');
        });
        
        // Add clear button to search input container
        const searchContainer = searchInput?.parentElement;
        if (searchContainer) {
            searchContainer.appendChild(clearSearchButton);
        }
    }
    
    // Function to remove clear button
    function removeClearButton() {
        const clearButton = document.getElementById('clear-search-btn');
        if (clearButton) {
            clearButton.remove();
        }
    }
    
    // Handle create form submission
    const createForm = document.querySelector('#drawer-create-news-portal-default form');
    if (createForm) {
        createForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => {
                if (response.ok) {
                    // Close drawer and reload page
                    const drawer = document.getElementById('drawer-create-news-portal-default');
                    const drawerInstance = new Drawer(drawer);
                    drawerInstance.hide();
                    window.location.reload();
                } else {
                    // Handle errors
                    console.error('Error creating portal');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Handle edit form submission
    const editForm = document.querySelector('#drawer-update-news-portal-default form');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error('Error updating portal');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Handle delete form submission
    const deleteForm = document.querySelector('#drawer-delete-news-portal-default form');
    if (deleteForm) {
        deleteForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error('Error deleting portal');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Populate edit form with portal data
    function populateEditForm(portalData) {
        const editForm = document.querySelector('#drawer-update-news-portal-default form');
        
        if (editForm) {
            // Update form action URL
            editForm.action = `/crawler/news-portals/${portalData.id}/edit/`;
            
            // Populate form fields
            const domainField = document.getElementById('edit_domain');
            const nameField = document.getElementById('edit_name');
            const newsScopeField = document.getElementById('edit_news_scope');
            const countryField = document.getElementById('edit_country');
            const cityField = document.getElementById('edit_city');
            
            if (domainField) domainField.value = portalData.domain || '';
            if (nameField) nameField.value = portalData.name || '';
            if (newsScopeField) newsScopeField.value = portalData.news_scope || 'national';
            if (countryField) countryField.value = portalData.country || '';
            if (cityField) cityField.value = portalData.city || '';
            

        }
    }
    
    // Populate delete form with portal data
    function populateDeleteForm(portalData) {
        const deleteForm = document.querySelector('#drawer-delete-news-portal-default form');
        
        if (deleteForm) {
            // Update form action URL
            deleteForm.action = `/crawler/news-portals/${portalData.id}/delete/`;

        }
    }
    
    // Add click handlers for edit buttons
    document.querySelectorAll('[data-drawer-target="drawer-update-news-portal-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get portal data from the row
            const row = this.closest('tr');
            
            const domainElement = row.querySelector('[data-field="domain"]');
            const nameElement = row.querySelector('[data-field="name"]');
            const newsScopeElement = row.querySelector('[data-field="news_scope"]');
            const countryElement = row.querySelector('[data-field="country"]');
            const cityElement = row.querySelector('[data-field="city"]');
            
            const portalData = {
                id: row.dataset.portalId,
                domain: domainElement?.textContent?.trim() || '',
                name: nameElement?.textContent?.trim() || '',
                news_scope: newsScopeElement?.dataset.value || 'national',
                country: countryElement?.dataset.value || '',
                city: cityElement?.textContent?.trim() || ''
            };
            
            // Clean up the data
            if (portalData.city === '-') portalData.city = '';
            if (portalData.country === '') portalData.country = '';
            
            populateEditForm(portalData);
        });
    });
    
    // Add click handlers for delete buttons
    document.querySelectorAll('[data-drawer-target="drawer-delete-news-portal-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get portal data from the row
            const row = this.closest('tr');
            const portalData = {
                id: row.dataset.portalId
            };
            
            populateDeleteForm(portalData);
        });
    });
    
}); 