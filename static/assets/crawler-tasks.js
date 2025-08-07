// Crawler Tasks JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize drawers manually if needed
    function initializeDrawers() {
        const drawerIds = [
            'drawer-create-crawler-task-default',
            'drawer-execute-crawler-task-default',
            'drawer-delete-crawler-task-default'
        ];
        
        drawerIds.forEach(drawerId => {
            const drawer = document.getElementById(drawerId);
            if (drawer) {
                // Check if drawer is already initialized
                let drawerInstance = null;
                try {
                    drawerInstance = window.Drawer.getInstance(drawer);
                } catch (e) {
                    // Drawer not initialized yet
                }
                
                if (!drawerInstance && window.Drawer) {
                    // Initialize drawer if it doesn't exist
                    try {
                        new window.Drawer(drawer, {
                            placement: 'right',
                            backdrop: true,
                            bodyScrolling: false,
                            edge: false,
                            edgeOffset: ''
                        });
                    } catch (e) {
                        // Drawer initialization failed, will use fallback
                    }
                }
            }
        });
    }
    
    // Initialize drawers
    initializeDrawers();
    
    // Search functionality
    const searchInput = document.getElementById('crawler-tasks-search');
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
    const createForm = document.querySelector('#drawer-create-crawler-task-default form');
    if (createForm) {
        createForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Clear previous error messages
            clearFormErrors();
            
            // Validate form before submission
            if (!validateForm()) {
                return;
            }
            
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
                    const drawer = document.getElementById('drawer-create-crawler-task-default');
                    if (drawer) {
                        let drawerInstance = null;
                        try {
                            drawerInstance = window.Drawer.getInstance(drawer);
                        } catch (e) {
                            // Drawer instance not found, using fallback
                        }
                        
                        if (drawerInstance) {
                            drawerInstance.hide();
                        } else {
                            // Fallback: hide the drawer manually
                            drawer.classList.add('translate-x-full');
                            drawer.classList.remove('transform-none');
                            drawer.setAttribute('inert', '');
                        }
                    }
                    
                    // Use a small timeout to ensure the drawer is hidden before reloading
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                } else {
                    // Handle errors - show error message or handle form errors
                    console.error('Error creating crawler task - Status:', response.status);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Function to validate form
    function validateForm() {
        let isValid = true;
        
        // Get form elements
        const crawlerConfigField = document.getElementById('crawler_config');
        
        // Validate crawler config
        if (!crawlerConfigField.value) {
            showFieldError(crawlerConfigField, 'Please select a crawler config');
            isValid = false;
        }
        
        return isValid;
    }
    
    // Function to show field error
    function showFieldError(field, message) {
        // Remove existing error
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Add error class to field
        field.classList.add('border-red-500');
        
        // Create error message element
        const errorElement = document.createElement('div');
        errorElement.className = 'field-error text-red-500 text-sm mt-1';
        errorElement.textContent = message;
        
        // Insert error message after the field
        field.parentNode.appendChild(errorElement);
    }
    
    // Function to clear form errors
    function clearFormErrors() {
        // Remove all error messages
        const errorElements = document.querySelectorAll('.field-error');
        errorElements.forEach(element => element.remove());
        
        // Remove error classes from fields
        const fields = document.querySelectorAll('#drawer-create-crawler-task-default input, #drawer-create-crawler-task-default select, #drawer-create-crawler-task-default textarea');
        fields.forEach(field => {
            field.classList.remove('border-red-500');
        });
    }
    
    // Handle execute task form submission
    const executeForm = document.querySelector('#drawer-execute-crawler-task-default form');
    if (executeForm) {
        executeForm.addEventListener('submit', function(e) {
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
                    const drawer = document.getElementById('drawer-execute-crawler-task-default');
                    if (drawer) {
                        let drawerInstance = null;
                        try {
                            drawerInstance = window.Drawer.getInstance(drawer);
                        } catch (e) {
                            // Drawer instance not found, using fallback
                        }
                        
                        if (drawerInstance) {
                            drawerInstance.hide();
                        } else {
                            // Fallback: hide the drawer manually
                            drawer.classList.add('translate-x-full');
                            drawer.classList.remove('transform-none');
                            drawer.setAttribute('inert', '');
                        }
                    }
                    
                    // Use a small timeout to ensure the drawer is hidden before reloading
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                } else {
                    console.error('Error executing crawler task');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Handle delete task form submission
    const deleteForm = document.querySelector('#drawer-delete-crawler-task-default form');
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
                    // Close drawer and reload page
                    const drawer = document.getElementById('drawer-delete-crawler-task-default');
                    if (drawer) {
                        let drawerInstance = null;
                        try {
                            drawerInstance = window.Drawer.getInstance(drawer);
                        } catch (e) {
                            // Drawer instance not found, using fallback
                        }
                        
                        if (drawerInstance) {
                            drawerInstance.hide();
                        } else {
                            // Fallback: hide the drawer manually
                            drawer.classList.add('translate-x-full');
                            drawer.classList.remove('transform-none');
                            drawer.setAttribute('inert', '');
                        }
                    }
                    
                    // Use a small timeout to ensure the drawer is hidden before reloading
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                } else {
                    console.error('Error deleting crawler task');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Populate execute form with task data
    function populateExecuteForm(taskData) {
        const executeForm = document.querySelector('#drawer-execute-crawler-task-default form');
        
        if (executeForm) {
            // Update form action URL
            executeForm.action = `/crawler/crawler-tasks/${taskData.id}/execute/`;
        }
    }
    
    // Populate delete form with task data
    function populateDeleteForm(taskData) {
        const deleteForm = document.querySelector('#drawer-delete-crawler-task-default form');
        
        if (deleteForm) {
            // Update form action URL
            deleteForm.action = `/crawler/crawler-tasks/${taskData.id}/delete/`;
        }
    }
    
    // Add click handlers for execute buttons
    document.querySelectorAll('[data-drawer-target="drawer-execute-crawler-task-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get task data from the row
            const row = this.closest('tr');
            const taskData = {
                id: row.dataset.taskId
            };
            
            populateExecuteForm(taskData);
        });
    });
    
    // Add click handlers for delete buttons
    document.querySelectorAll('[data-drawer-target="drawer-delete-crawler-task-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get task data from the row
            const row = this.closest('tr');
            const taskData = {
                id: row.dataset.taskId
            };
            
            populateDeleteForm(taskData);
        });
    });
    
}); 