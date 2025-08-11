// Crawler Configs JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize drawers manually if needed
    function initializeDrawers() {
        const drawerIds = [
            'drawer-create-crawler-config-default',
            'drawer-update-crawler-config-default',
            'drawer-delete-crawler-config-default'
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
    const searchInput = document.getElementById('crawler-configs-search');
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
    const createForm = document.querySelector('#drawer-create-crawler-config-default form');
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

            // Collect selected seed URLs
            const seedCheckboxes = document.querySelectorAll('#seed-url-list .seed-checkbox:checked');
            const selectedSeeds = Array.from(seedCheckboxes).map(cb => cb.value);
            if (selectedSeeds.length > 0) {
                // Append as multiple values
                selectedSeeds.forEach(url => formData.append('seed_urls', url));
            }
            
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
                    const drawer = document.getElementById('drawer-create-crawler-config-default');
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
                    console.error('Error creating crawler config - Status:', response.status);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    } else {
        // Create form not found
        console.warn('Create form not found - selector: #drawer-create-crawler-config-default form');
    }
    
    // Function to validate form
    function validateForm() {
        let isValid = true;
        
        // Get form elements
        const nameField = document.getElementById('name');
        const portalField = document.getElementById('portal');
        const itemSelectorField = document.getElementById('item_selector');
        const customSettingsField = document.getElementById('custom_settings');
        
        // Validate name
        if (!nameField.value.trim()) {
            showFieldError(nameField, 'Name is required');
            isValid = false;
        }
        
        // Validate portal
        if (!portalField.value) {
            showFieldError(portalField, 'Please select a portal');
            isValid = false;
        }
        
        // Validate item selector
        if (!itemSelectorField.value) {
            showFieldError(itemSelectorField, 'Please select an item selector');
            isValid = false;
        }
        
        // Validate custom settings (JSON format)
        if (customSettingsField.value.trim()) {
            try {
                const customSettings = customSettingsField.value.trim();
                if (customSettings !== '' && customSettings !== '{}') {
                    JSON.parse(customSettings);
                }
            } catch (error) {
                showFieldError(customSettingsField, 'Please enter valid JSON format');
                isValid = false;
            }
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
        const fields = document.querySelectorAll('#drawer-create-crawler-config-default input, #drawer-create-crawler-config-default select, #drawer-create-crawler-config-default textarea');
        fields.forEach(field => {
            field.classList.remove('border-red-500');
        });
    }
    
    // Add real-time validation for custom_settings field
    const customSettingsField = document.getElementById('custom_settings');
    if (customSettingsField) {
        customSettingsField.addEventListener('input', function() {
            // Clear previous error for this field
            const existingError = this.parentNode.querySelector('.field-error');
            if (existingError) {
                existingError.remove();
            }
            this.classList.remove('border-red-500');
            
            // Validate JSON format if field has content
            if (this.value.trim() && this.value.trim() !== '{}') {
                try {
                    JSON.parse(this.value.trim());
                    // Valid JSON - no error to show
                } catch (error) {
                    showFieldError(this, 'Please enter valid JSON format');
                }
            }
        });
    }
    
    // Handle edit form submission
    const editForm = document.querySelector('#drawer-update-crawler-config-default form');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Clear previous error messages
            clearEditFormErrors();
            
            // Validate form before submission
            if (!validateEditForm()) {
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
                    const drawer = document.getElementById('drawer-update-crawler-config-default');
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
                            // Fallback: hide the drawer manually with proper focus handling
                            // Remove focus from any element inside the drawer
                            const focusedElement = drawer.querySelector(':focus');
                            if (focusedElement) {
                                focusedElement.blur();
                            }
                            
                            // Hide the drawer
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
                    console.error('Error updating crawler config');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Function to validate edit form
    function validateEditForm() {
        let isValid = true;
        
        // Get form elements
        const nameField = document.getElementById('edit_name');
        const portalField = document.getElementById('edit_portal');
        const itemSelectorField = document.getElementById('edit_item_selector');
        const customSettingsField = document.getElementById('edit_custom_settings');
        
        // Validate name
        if (!nameField.value.trim()) {
            showEditFieldError(nameField, 'Name is required');
            isValid = false;
        }
        
        // Validate portal
        if (!portalField.value) {
            showEditFieldError(portalField, 'Please select a portal');
            isValid = false;
        }
        
        // Validate item selector
        if (!itemSelectorField.value) {
            showEditFieldError(itemSelectorField, 'Please select an item selector');
            isValid = false;
        }
        
        // Validate custom settings (JSON format)
        if (customSettingsField.value.trim()) {
            try {
                const customSettings = customSettingsField.value.trim();
                if (customSettings !== '' && customSettings !== '{}') {
                    JSON.parse(customSettings);
                }
            } catch (error) {
                showEditFieldError(customSettingsField, 'Please enter valid JSON format');
                isValid = false;
            }
        }
        
        return isValid;
    }
    
    // Function to show edit field error
    function showEditFieldError(field, message) {
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
    
    // Function to clear edit form errors
    function clearEditFormErrors() {
        // Remove all error messages
        const errorElements = document.querySelectorAll('#drawer-update-crawler-config-default .field-error');
        errorElements.forEach(element => element.remove());
        
        // Remove error classes from fields
        const fields = document.querySelectorAll('#drawer-update-crawler-config-default input, #drawer-update-crawler-config-default select, #drawer-update-crawler-config-default textarea');
        fields.forEach(field => {
            field.classList.remove('border-red-500');
        });
    }
    
    // Add real-time validation for edit custom_settings field
    const editCustomSettingsField = document.getElementById('edit_custom_settings');
    if (editCustomSettingsField) {
        editCustomSettingsField.addEventListener('input', function() {
            // Clear previous error for this field
            const existingError = this.parentNode.querySelector('.field-error');
            if (existingError) {
                existingError.remove();
            }
            this.classList.remove('border-red-500');
            
            // Validate JSON format if field has content
            if (this.value.trim() && this.value.trim() !== '{}') {
                try {
                    JSON.parse(this.value.trim());
                    // Valid JSON - no error to show
                } catch (error) {
                    showEditFieldError(this, 'Please enter valid JSON format');
                }
            }
        });
    }
    
    // Handle delete form submission
    const deleteForm = document.querySelector('#drawer-delete-crawler-config-default form');
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
                    const drawer = document.getElementById('drawer-delete-crawler-config-default');
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
                            // Fallback: hide the drawer manually with proper focus handling
                            // Remove focus from any element inside the drawer
                            const focusedElement = drawer.querySelector(':focus');
                            if (focusedElement) {
                                focusedElement.blur();
                            }
                            
                            // Hide the drawer
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
                    console.error('Error deleting crawler config');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
    
    // Populate edit form with config data
    function populateEditForm(configData) {
        const editForm = document.querySelector('#drawer-update-crawler-config-default form');
        
        if (editForm) {
            // Update form action URL
            editForm.action = `/crawler/crawler-configs/${configData.id}/edit/`;
            
            // Populate form fields
            const nameField = document.getElementById('edit_name');
            const portalField = document.getElementById('edit_portal');
            const itemSelectorField = document.getElementById('edit_item_selector');
            const customSettingsField = document.getElementById('edit_custom_settings');
            const editSeedList = document.getElementById('edit-seed-url-list');
            const row = document.querySelector(`tr[data-config-id="${configData.id}"]`);
            
            if (nameField) nameField.value = configData.name || '';
            if (portalField) portalField.value = row?.dataset.portalId || '';
            if (itemSelectorField) itemSelectorField.value = row?.dataset.itemSelectorId || '';
            if (customSettingsField) {
                let cs = row?.dataset.customSettings || '';
                if (!cs || cs === '{}' || cs === 'null') cs = '{"delay": 1}';
                customSettingsField.value = cs;
            }

            // Preselect seed URLs from custom_settings if present
            try {
                const csObj = JSON.parse(row?.dataset.customSettings || '{}');
                const currentSeeds = Array.isArray(csObj.seed_urls) ? csObj.seed_urls : [];
                if (editSeedList) {
                    editSeedList.querySelectorAll('.edit-seed-checkbox').forEach(cb => {
                        cb.checked = currentSeeds.includes(cb.value);
                    });
                }
            } catch (e) {
                // ignore
            }
        }
    }
    
    // Populate delete form with config data
    function populateDeleteForm(configData) {
        const deleteForm = document.querySelector('#drawer-delete-crawler-config-default form');
        
        if (deleteForm) {
            // Update form action URL
            deleteForm.action = `/crawler/crawler-configs/${configData.id}/delete/`;
        }
    }
    
    // Add click handlers for edit buttons
    document.querySelectorAll('[data-drawer-target="drawer-update-crawler-config-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get config data from the row
            const row = this.closest('tr');
            
            const nameElement = row.querySelector('[data-field="name"]');
            const portalNameElement = row.querySelector('[data-field="portal_name"]');
            const itemSelectorQueryElement = row.querySelector('[data-field="item_selector_query"]');
            const customSettingsElement = row.querySelector('[data-field="custom_settings"]');
            
            const configData = {
                id: row.dataset.configId,
                name: nameElement?.textContent?.trim() || '',
                portal: portalNameElement?.textContent?.trim() || '',
                item_selector: itemSelectorQueryElement?.textContent?.trim() || '',
                custom_settings: customSettingsElement?.textContent?.trim() || ''
            };
            
            populateEditForm(configData);
        });
    });

    // Filter seed list by selected portal (Create)
    const portalHidden = document.getElementById('portal');
    const seedList = document.getElementById('seed-url-list');
    const seedSearch = document.getElementById('seed-url-search');
    function refreshSeedVisibility(listEl, portalId, searchValue, itemSelector) {
        const term = (searchValue || '').toLowerCase();
        listEl.querySelectorAll(itemSelector).forEach(label => {
            const belongs = !portalId || label.dataset.portal === portalId;
            const text = label.textContent.toLowerCase();
            const matches = text.includes(term);
            label.style.display = belongs && matches ? 'flex' : 'none';
        });
    }
    if (portalHidden && seedList) {
        portalHidden.addEventListener('change', () => refreshSeedVisibility(seedList, portalHidden.value, seedSearch?.value, '.seed-item'));
        if (seedSearch) seedSearch.addEventListener('input', () => refreshSeedVisibility(seedList, portalHidden.value, seedSearch.value, '.seed-item'));
        refreshSeedVisibility(seedList, portalHidden.value, seedSearch?.value, '.seed-item');
    }

    // Filter seed list by selected portal (Edit)
    const editPortalHidden = document.getElementById('edit_portal');
    const editSeedList = document.getElementById('edit-seed-url-list');
    const editSeedSearch = document.getElementById('edit-seed-url-search');
    if (editPortalHidden && editSeedList) {
        editPortalHidden.addEventListener('change', () => refreshSeedVisibility(editSeedList, editPortalHidden.value, editSeedSearch?.value, '.edit-seed-item'));
        if (editSeedSearch) editSeedSearch.addEventListener('input', () => refreshSeedVisibility(editSeedList, editPortalHidden.value, editSeedSearch.value, '.edit-seed-item'));
        refreshSeedVisibility(editSeedList, editPortalHidden.value, editSeedSearch?.value, '.edit-seed-item');
    }
    
    // Add click handlers for delete buttons
    document.querySelectorAll('[data-drawer-target="drawer-delete-crawler-config-default"]').forEach(button => {
        button.addEventListener('click', function() {
            // Get config data from the row
            const row = this.closest('tr');
            const configData = {
                id: row.dataset.configId
            };
            
            populateDeleteForm(configData);
        });
    });
    
}); 