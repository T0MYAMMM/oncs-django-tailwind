// Selectors JavaScript functionality
// Immediately override initDrawers to prevent any drawer initialization
if (window.initDrawers) {
    window.initDrawers = function() {
        console.log('initDrawers blocked immediately');
        return;
    };
}

document.addEventListener('DOMContentLoaded', function() {
    
    // Debug: Check if Flowbite is loaded
    console.log('window.FlowbiteInstances:', window.FlowbiteInstances);
    console.log('window.initFlowbite:', window.initFlowbite);
    
    // Completely disable Flowbite drawer functionality
    if (window.FlowbiteInstances) {
        // Override the initDrawers method to prevent automatic drawer initialization
        const originalInitDrawers = window.FlowbiteInstances.initDrawers;
        if (originalInitDrawers) {
            window.FlowbiteInstances.initDrawers = function() {
                console.log('Preventing Flowbite from auto-initializing drawers');
                // Don't call the original method
                return;
            };
        }
    }
    
    // Also override the global initDrawers function
    if (window.initDrawers) {
        window.initDrawers = function() {
            console.log('Preventing global initDrawers from running');
            return;
        };
    }
    
    // Override the Drawer class to prevent any drawer operations
    if (window.Drawer) {
        const OriginalDrawer = window.Drawer;
        window.Drawer = function() {
            console.log('Preventing Drawer class instantiation');
            return {
                show: function() { console.log('Drawer.show() blocked'); },
                hide: function() { console.log('Drawer.hide() blocked'); },
                toggle: function() { console.log('Drawer.toggle() blocked'); }
            };
        };
        // Copy static methods if they exist
        if (OriginalDrawer.getInstance) {
            window.Drawer.getInstance = function() {
                console.log('Drawer.getInstance() blocked');
                return null;
            };
        }
    }
    
    // Override initFlowbite to prevent drawer initialization
    if (window.initFlowbite) {
        const originalInitFlowbite = window.initFlowbite;
        window.initFlowbite = function() {
            console.log('Intercepting initFlowbite to prevent drawer initialization');
            // Call the original but intercept the drawer part
            const result = originalInitFlowbite.call(this);
            
            // Immediately override initDrawers again after initFlowbite runs
            if (window.initDrawers) {
                window.initDrawers = function() {
                    console.log('Preventing initDrawers from running after initFlowbite');
                    return;
                };
            }
            
            return result;
        };
    }
    
    // Initialize native HTML drawer functionality
    function initializeDrawers() {
        const drawerIds = [
            'drawer-create-selector-default',
            'drawer-update-selector-default',
            'drawer-delete-selector-default'
        ];
        
        drawerIds.forEach(drawerId => {
            const drawer = document.getElementById(drawerId);
            if (drawer) {
                console.log(`Initializing native drawer: ${drawerId}`);
                
                // Add click event to backdrop for closing
                const backdrop = drawer.querySelector('[data-drawer-backdrop]');
                if (backdrop) {
                    backdrop.addEventListener('click', () => {
                        closeDrawer(drawerId);
                    });
                }
                
                // Add escape key support
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape' && !drawer.classList.contains('translate-x-full')) {
                        closeDrawer(drawerId);
                    }
                });
            }
        });
        
        // Add click handlers for buttons to open drawers
        const createButton = document.getElementById('createSelectorButton');
        if (createButton) {
            createButton.addEventListener('click', () => {
                openDrawer('drawer-create-selector-default');
            });
        }
        
        // Add handlers for edit and delete buttons (these are added dynamically)
        document.addEventListener('click', (e) => {
            if (e.target.closest('#updateSelectorButton')) {
                openDrawer('drawer-update-selector-default');
            }
            if (e.target.closest('#deleteSelectorButton')) {
                openDrawer('drawer-delete-selector-default');
            }
        });
    }
    
    // Function to open drawer
    function openDrawer(drawerId) {
        const drawer = document.getElementById(drawerId);
        if (drawer) {
            drawer.classList.remove('translate-x-full');
            drawer.classList.add('transform-none');
            drawer.setAttribute('aria-hidden', 'false');
            drawer.removeAttribute('inert');
            console.log(`Opened drawer: ${drawerId}`);
        }
    }
    
    // Function to close drawer
    function closeDrawer(drawerId) {
        const drawer = document.getElementById(drawerId);
        if (drawer) {
            drawer.classList.add('translate-x-full');
            drawer.classList.remove('transform-none');
            drawer.setAttribute('aria-hidden', 'true');
            drawer.setAttribute('inert', '');
            console.log(`Closed drawer: ${drawerId}`);
        }
    }
    
    // Initialize drawers after a short delay
    setTimeout(initializeDrawers, 100);
    
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
        console.log('Create form found, adding submit handler');
        createForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Form submission intercepted');
            
            const formData = new FormData(this);
            console.log('Form action:', this.action);
            
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
                    closeDrawer('drawer-create-selector-default');
                    // Show success message
                    const successMessage = document.createElement('div');
                    successMessage.className = 'fixed top-4 right-4 z-50 p-4 bg-green-500 text-white rounded-lg shadow-lg';
                    successMessage.textContent = 'Selector created successfully!';
                    document.body.appendChild(successMessage);
                    
                    // Remove message and reload after a short delay
                    setTimeout(() => {
                        successMessage.remove();
                        window.location.reload();
                    }, 1500);
                } else {
                    // Handle errors
                    console.error('Error creating selector');
                    alert('Error creating selector. Please try again.');
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
            editForm.action = `/common/selectors/${selectorData.id}/edit/`;
            
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
            deleteForm.action = `/common/selectors/${selectorData.id}/delete/`;
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