// Selectors JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    
    // Search functionality
    const searchInput = document.getElementById('selectors-search');
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
    const createForm = document.querySelector('#drawer-create-selector-default form');
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
                    const drawer = document.getElementById('drawer-create-selector-default');
                    if (drawer) {
                        // Use Flowbite drawer hide method
                        const drawerInstance = window.Drawer.getInstance(drawer);
                        if (drawerInstance) {
                            drawerInstance.hide();
                        } else {
                            // Fallback: hide the drawer manually
                            drawer.classList.add('translate-x-full');
                            drawer.setAttribute('aria-hidden', 'true');
                        }
                    }
                    window.location.reload();
                } else {
                    // Handle errors
                    console.error('Error creating selector');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Handle edit form submission
    const editForm = document.querySelector('#drawer-update-selector-default form');
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
                    console.error('Error updating selector');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Handle delete form submission
    const deleteForm = document.querySelector('#drawer-delete-selector-default form');
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
                    console.error('Error deleting selector');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Populate edit form with selector data
    function populateEditForm(selectorData) {
        const editForm = document.querySelector('#drawer-update-selector-default form');
        
        if (editForm) {
            // Update form action URL
            editForm.action = `/crawler/selectors/${selectorData.id}/edit/`;
            
            // Populate form fields
            const portalField = document.getElementById('edit_portal');
            const queryField = document.getElementById('edit_query');
            const itemField = document.getElementById('edit_item');
            const methodField = document.getElementById('edit_method');
            
            if (portalField) portalField.value = selectorData.portal || '';
            if (queryField) queryField.value = selectorData.query || '';
            if (itemField) itemField.value = selectorData.item || 'url_list';
            if (methodField) methodField.value = selectorData.method || 'css';
        }
    }
    
    // Populate delete form with selector data
    function populateDeleteForm(selectorData) {
        const deleteForm = document.querySelector('#drawer-delete-selector-default form');
        
        if (deleteForm) {
            // Update form action URL
            deleteForm.action = `/crawler/selectors/${selectorData.id}/delete/`;
        }
    }
    
    // Add click handlers for edit buttons
    document.querySelectorAll('[data-drawer-target="drawer-update-selector-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get selector data from the row
            const row = this.closest('tr');
            
            const portalNameElement = row.querySelector('[data-field="portal_name"]');
            const portalDomainElement = row.querySelector('[data-field="portal_domain"]');
            const itemElement = row.querySelector('[data-field="item"]');
            const methodElement = row.querySelector('[data-field="method"]');
            const queryElement = row.querySelector('[data-field="query"]');
            
            const selectorData = {
                id: row.dataset.selectorId,
                portal: portalNameElement?.textContent?.trim() || '',
                portal_domain: portalDomainElement?.textContent?.trim() || '',
                item: itemElement?.dataset.value || 'url_list',
                method: methodElement?.dataset.value || 'css',
                query: queryElement?.textContent?.trim() || ''
            };
            
            populateEditForm(selectorData);
        });
    });
    
    // Add click handlers for delete buttons
    document.querySelectorAll('[data-drawer-target="drawer-delete-selector-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get selector data from the row
            const row = this.closest('tr');
            const selectorData = {
                id: row.dataset.selectorId
            };
            
            populateDeleteForm(selectorData);
        });
    });
    
}); 