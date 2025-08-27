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
        const proxySettingsField = document.getElementById('proxy_settings');
        const customHeadersField = document.getElementById('custom_headers');
        
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
        
        // Validate proxy settings (JSON format)
        if (proxySettingsField.value.trim()) {
            try {
                const proxySettings = proxySettingsField.value.trim();
                if (proxySettings !== '' && proxySettings !== '{}') {
                    JSON.parse(proxySettings);
                }
            } catch (error) {
                showFieldError(proxySettingsField, 'Please enter valid JSON format for proxy settings');
                isValid = false;
            }
        }
        
        // Validate custom headers (JSON format)
        if (customHeadersField.value.trim()) {
            try {
                const customHeaders = customHeadersField.value.trim();
                if (customHeaders !== '' && customHeaders !== '{}') {
                    JSON.parse(customHeaders);
                }
            } catch (error) {
                showFieldError(customHeadersField, 'Please enter valid JSON format for custom headers');
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
    
    // Add real-time validation for proxy_settings field
    const proxySettingsField = document.getElementById('proxy_settings');
    if (proxySettingsField) {
        proxySettingsField.addEventListener('input', function() {
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
                    showFieldError(this, 'Please enter valid JSON format for proxy settings');
                }
            }
        });
    }
    
    // Add real-time validation for custom_headers field
    const customHeadersField = document.getElementById('custom_headers');
    if (customHeadersField) {
        customHeadersField.addEventListener('input', function() {
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
                    showFieldError(this, 'Please enter valid JSON format for custom headers');
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
        const proxySettingsField = document.getElementById('edit_proxy_settings');
        const customHeadersField = document.getElementById('edit_custom_headers');
        
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
        
        // Validate proxy settings (JSON format)
        if (proxySettingsField.value.trim()) {
            try {
                const proxySettings = proxySettingsField.value.trim();
                if (proxySettings !== '' && proxySettings !== '{}') {
                    JSON.parse(proxySettings);
                }
            } catch (error) {
                showEditFieldError(proxySettingsField, 'Please enter valid JSON format for proxy settings');
                isValid = false;
            }
        }
        
        // Validate custom headers (JSON format)
        if (customHeadersField.value.trim()) {
            try {
                const customHeaders = customHeadersField.value.trim();
                if (customHeaders !== '' && customHeaders !== '{}') {
                    JSON.parse(customHeaders);
                }
            } catch (error) {
                showEditFieldError(customHeadersField, 'Please enter valid JSON format for custom headers');
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
    
    // Add real-time validation for edit proxy_settings field
    const editProxySettingsField = document.getElementById('edit_proxy_settings');
    if (editProxySettingsField) {
        editProxySettingsField.addEventListener('input', function() {
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
                    showEditFieldError(this, 'Please enter valid JSON format for proxy settings');
                }
            }
        });
    }
    
    // Add real-time validation for edit custom_headers field
    const editCustomHeadersField = document.getElementById('edit_custom_headers');
    if (editCustomHeadersField) {
        editCustomHeadersField.addEventListener('input', function() {
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
                    showEditFieldError(this, 'Please enter valid JSON format for custom headers');
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
    
    // Function to wait for dropdowns to be populated
    function waitForDropdowns(callback, maxAttempts = 10) {
        let attempts = 0;
        
        function checkDropdowns() {
            const portalDropdown = document.getElementById('edit-portal-dropdown');
            const selectorDropdown = document.getElementById('edit-selector-dropdown');
            
            if (portalDropdown && selectorDropdown) {
                const portalOptions = portalDropdown.querySelectorAll('.edit-portal-option');
                const selectorOptions = selectorDropdown.querySelectorAll('.edit-selector-option');
                
                if (portalOptions.length > 0 && selectorOptions.length > 0) {
                    console.log('Dropdowns are populated, executing callback');
                    callback();
                    return;
                }
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                console.log(`Dropdowns not ready yet, attempt ${attempts}/${maxAttempts}, retrying in 100ms`);
                setTimeout(checkDropdowns, 100);
            } else {
                console.warn('Dropdowns not populated after maximum attempts, executing callback anyway');
                callback();
            }
        }
        
        checkDropdowns();
    }

    // Populate edit form with config data
    function populateEditForm(configData) {
        console.log('Populating edit form with data:', configData);
        
        // Wait for dropdowns to be populated before proceeding
        waitForDropdowns(() => {
            populateEditFormInternal(configData);
        });
    }
    
    // Internal function to populate the form (called after dropdowns are ready)
    function populateEditFormInternal(configData) {
        const editForm = document.querySelector('#drawer-update-crawler-config-default form');
        
        if (editForm) {
            // Update form action URL
            editForm.action = `/crawler/crawler-configs/${configData.id}/edit/`;
            
            // Populate form fields
            const nameField = document.getElementById('edit_name');
            const portalField = document.getElementById('edit_portal');
            const portalSearchField = document.getElementById('edit-portal-search');
            const itemSelectorField = document.getElementById('edit_item_selector');
            const itemSelectorSearchField = document.getElementById('edit-selector-search');
            const customSettingsField = document.getElementById('edit_custom_settings');
            const editSeedList = document.getElementById('edit-seed-url-list');
            const row = document.querySelector(`tr[data-config-id="${configData.id}"]`);
            
            console.log('Found row:', row);
            console.log('Row dataset:', row?.dataset);
            
            // Check if dropdowns are populated
            const portalDropdown = document.getElementById('edit-portal-dropdown');
            const selectorDropdown = document.getElementById('edit-selector-dropdown');
            
            if (portalDropdown) {
                const portalOptions = portalDropdown.querySelectorAll('.edit-portal-option');
                console.log('Portal dropdown options found:', portalOptions.length);
                portalOptions.forEach((option, index) => {
                    console.log(`Portal option ${index}:`, option.dataset.value, option.dataset.text);
                });
            }
            
            if (selectorDropdown) {
                const selectorOptions = selectorDropdown.querySelectorAll('.edit-selector-option');
                console.log('Selector dropdown options found:', selectorOptions.length);
                selectorOptions.forEach((option, index) => {
                    console.log(`Selector option ${index}:`, option.dataset.value, option.dataset.text);
                });
            }
            
            if (nameField) nameField.value = configData.name || '';
            
            // Handle portal field - get the actual portal ID and text from the table row
            if (portalField && portalSearchField) {
                const portalId = row?.dataset.portalId || '';
                const portalName = row?.dataset.portalName || '';
                
                console.log('Portal ID from row:', portalId);
                console.log('Portal name from row:', portalName);
                
                // Find the portal option that matches the ID
                const portalOptions = document.querySelectorAll('#edit-portal-dropdown .edit-portal-option');
                console.log('Found portal options:', portalOptions.length);
                
                let portalText = '';
                
                portalOptions.forEach(option => {
                    console.log('Portal option:', option.dataset.value, option.dataset.text);
                    if (option.dataset.value === portalId) {
                        portalText = option.dataset.text;
                        console.log('Matched portal:', portalText);
                    }
                });
                
                portalField.value = portalId;
                portalSearchField.value = portalText;
                
                console.log('Set portal field value:', portalId);
                console.log('Set portal search field value:', portalText);
                
                // Refresh seed visibility for the selected portal
                if (editSeedList) {
                    refreshSeedVisibility(editSeedList, portalId, '', '.edit-seed-item');
                    updateSeedUrlCount(portalId, 'edit-seed-url-count');
                }
            }
            
            // Handle item selector field - get the actual selector ID and text from the table row
            if (itemSelectorField && itemSelectorSearchField) {
                const selectorId = row?.dataset.itemSelectorId || '';
                const selectorQuery = row?.dataset.itemSelectorQuery || '';
                
                console.log('Selector ID from row:', selectorId);
                console.log('Selector query from row:', selectorQuery);
                
                // Find the selector option that matches the ID
                const selectorOptions = document.querySelectorAll('#edit-selector-dropdown .edit-selector-option');
                console.log('Found selector options:', selectorOptions.length);
                
                let selectorText = '';
                
                selectorOptions.forEach(option => {
                    console.log('Selector option:', option.dataset.value, option.dataset.text);
                    if (option.dataset.value === selectorId) {
                        selectorText = option.dataset.text;
                        console.log('Matched selector:', selectorText);
                    }
                });
                
                itemSelectorField.value = selectorId;
                itemSelectorSearchField.value = selectorText;
                
                console.log('Set selector field value:', selectorId);
                console.log('Set selector search field value:', selectorText);
            }
            
            if (customSettingsField) {
                let cs = configData.custom_settings || '';
                if (!cs || cs === '{}' || cs === 'null') cs = '{"delay": 1}';
                // Fix JSON encoding issues - replace escaped quotes and decode
                try {
                    cs = cs.replace(/\\u0027/g, "'").replace(/\\u0022/g, '"');
                    // Try to parse and re-stringify to ensure valid JSON
                    const parsed = JSON.parse(cs);
                    cs = JSON.stringify(parsed, null, 2);
                } catch (e) {
                    // If parsing fails, use the cleaned string
                    cs = cs.replace(/\\u0027/g, "'").replace(/\\u0022/g, '"');
                }
                customSettingsField.value = cs;
            }
            
            // Handle proxy settings field
            const proxySettingsField = document.getElementById('edit_proxy_settings');
            if (proxySettingsField) {
                let ps = configData.proxy_settings || '';
                if (!ps || ps === '{}' || ps === 'null') ps = '{"enable": false, "auto_rotate": false, "specific_proxy_type": "local"}';
                // Fix JSON encoding issues
                try {
                    ps = ps.replace(/\\u0027/g, "'").replace(/\\u0022/g, '"');
                    const parsed = JSON.parse(ps);
                    ps = JSON.stringify(parsed, null, 2);
                } catch (e) {
                    ps = ps.replace(/\\u0027/g, "'").replace(/\\u0022/g, '"');
                }
                proxySettingsField.value = ps;
            }
            
            // Handle custom headers field
            const customHeadersField = document.getElementById('edit_custom_headers');
            if (customHeadersField) {
                let ch = configData.custom_headers || '';
                if (!ch || ch === '{}' || ch === 'null') ch = '{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"}';
                // Fix JSON encoding issues
                try {
                    ch = ch.replace(/\\u0027/g, "'").replace(/\\u0022/g, '"');
                    const parsed = JSON.parse(ch);
                    ch = JSON.stringify(parsed, null, 2);
                } catch (e) {
                    ch = ch.replace(/\\u0027/g, "'").replace(/\\u0022/g, '"');
                }
                customHeadersField.value = ch;
            }

            // Preselect seed URLs from custom_settings if present
            try {
                // Use the cleaned custom settings from the field
                const customSettingsValue = customSettingsField ? customSettingsField.value : configData.custom_settings || '{}';
                console.log('Custom settings value for seed URLs:', customSettingsValue);
                
                const csObj = JSON.parse(customSettingsValue);
                console.log('Parsed custom settings object:', csObj);
                
                const currentSeeds = Array.isArray(csObj.seed_urls) ? csObj.seed_urls : [];
                console.log('Current seeds from custom settings:', currentSeeds);
                
                if (editSeedList) {
                    const checkboxes = editSeedList.querySelectorAll('.edit-seed-checkbox');
                    console.log('Found seed URL checkboxes:', checkboxes.length);
                    
                    checkboxes.forEach(cb => {
                        const isChecked = currentSeeds.includes(cb.value);
                        cb.checked = isChecked;
                        console.log('Seed URL checkbox:', cb.value, 'checked:', isChecked);
                    });
                }
            } catch (e) {
                console.warn('Error parsing custom settings for seed URLs:', e);
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
            console.log('Edit button clicked, row:', row);
            console.log('Row dataset:', row?.dataset);
            
            const nameElement = row.querySelector('[data-field="name"]');
            const portalNameElement = row.querySelector('[data-field="portal_name"]');
            const itemSelectorQueryElement = row.querySelector('[data-field="item_selector_query"]');
            const customSettingsElement = row.querySelector('[data-field="custom_settings"]');
            
            console.log('Name element:', nameElement?.textContent?.trim());
            console.log('Portal name element:', portalNameElement?.textContent?.trim());
            console.log('Item selector query element:', itemSelectorQueryElement?.textContent?.trim());
            console.log('Custom settings element:', customSettingsElement?.textContent?.trim());
            
            const configData = {
                id: row.dataset.configId,
                name: nameElement?.textContent?.trim() || '',
                portal: portalNameElement?.textContent?.trim() || '',
                item_selector: itemSelectorQueryElement?.textContent?.trim() || '',
                custom_settings: customSettingsElement?.textContent?.trim() || '',
                proxy_settings: row.dataset.proxySettings || '',
                custom_headers: row.dataset.customHeaders || ''
            };
            
            console.log('Config data prepared:', configData);
            
            populateEditForm(configData);
        });
    });

    // Initialize seed URL counts
    function initializeSeedUrlCounts() {
        // Initialize create form count
        const createPortalHidden = document.getElementById('portal');
        if (createPortalHidden) {
            updateSeedUrlCount(createPortalHidden.value, 'seed-url-count');
        }
        
        // Initialize edit form count
        const editPortalHidden = document.getElementById('edit_portal');
        if (editPortalHidden) {
            updateSeedUrlCount(editPortalHidden.value, 'edit-seed-url-count');
        }
    }
    
    // Initialize counts when page loads
    initializeSeedUrlCounts();
    
    // Function to update seed URL count
    function updateSeedUrlCount(portalId, countElementId) {
        const countElement = document.getElementById(countElementId);
        if (countElement) {
            const seedItems = document.querySelectorAll(`#${countElementId.replace('-count', '-list')} .seed-item, #${countElementId.replace('-count', '-list')} .edit-seed-item`);
            let count = 0;
            seedItems.forEach(item => {
                if (!portalId || item.dataset.portal === portalId) {
                    count++;
                }
            });
            countElement.textContent = count;
        }
    }

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
        
        // Update count for create form
        if (listEl.id === 'seed-url-list') {
            updateSeedUrlCount(portalId, 'seed-url-count');
        }
        // Update count for edit form
        if (listEl.id === 'edit-seed-url-list') {
            updateSeedUrlCount(portalId, 'edit-seed-url-count');
        }
    }
    if (portalHidden && seedList) {
        portalHidden.addEventListener('change', () => {
            refreshSeedVisibility(seedList, portalHidden.value, seedSearch?.value, '.seed-item');
            updateSeedUrlCount(portalHidden.value, 'seed-url-count');
        });
        if (seedSearch) seedSearch.addEventListener('input', () => {
            refreshSeedVisibility(seedList, portalHidden.value, seedSearch.value, '.seed-item');
            // Update count based on current portal selection
            if (portalHidden.value) {
                updateSeedUrlCount(portalHidden.value, 'seed-url-count');
            }
        });
        refreshSeedVisibility(seedList, portalHidden.value, seedSearch?.value, '.seed-item');
        
        // Initial count update
        updateSeedUrlCount(portalHidden.value, 'seed-url-count');
    }

    // Handle portal search and dropdown for create form
    const portalSearch = document.getElementById('portal-search');
    const portalDropdown = document.getElementById('portal-dropdown');
    
    if (portalSearch && portalDropdown && portalHidden) {
        // Show dropdown on focus
        portalSearch.addEventListener('focus', () => {
            portalDropdown.classList.remove('hidden');
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!portalSearch.contains(e.target) && !portalDropdown.contains(e.target)) {
                portalDropdown.classList.add('hidden');
            }
        });
        
        // Handle portal selection
        portalDropdown.querySelectorAll('.portal-option').forEach(option => {
            option.addEventListener('click', () => {
                const value = option.dataset.value;
                const text = option.dataset.text;
                portalHidden.value = value;
                portalSearch.value = text;
                portalDropdown.classList.add('hidden');
                
                // Refresh seed visibility and update count
                if (seedList) {
                    refreshSeedVisibility(seedList, value, seedSearch?.value, '.seed-item');
                    updateSeedUrlCount(value, 'seed-url-count');
                }
            });
        });
        
        // Filter portals on input
        portalSearch.addEventListener('input', () => {
            const searchTerm = portalSearch.value.toLowerCase();
            portalDropdown.querySelectorAll('.portal-option').forEach(option => {
                const text = option.dataset.text.toLowerCase();
                option.style.display = text.includes(searchTerm) ? 'block' : 'none';
            });
            
            // Update count based on current portal selection
            if (portalHidden.value) {
                updateSeedUrlCount(portalHidden.value, 'seed-url-count');
            }
        });
    }
    
    // Handle item selector search and dropdown for create form
    const selectorSearch = document.getElementById('selector-search');
    const selectorDropdown = document.getElementById('selector-dropdown');
    const itemSelectorHidden = document.getElementById('item_selector');
    
    if (selectorSearch && selectorDropdown && itemSelectorHidden) {
        // Show dropdown on focus
        selectorSearch.addEventListener('focus', () => {
            selectorDropdown.classList.remove('hidden');
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!selectorSearch.contains(e.target) && !selectorDropdown.contains(e.target)) {
                selectorDropdown.classList.add('hidden');
            }
        });
        
        // Handle selector selection
        selectorDropdown.querySelectorAll('.selector-option').forEach(option => {
            option.addEventListener('click', () => {
                const value = option.dataset.value;
                const text = option.dataset.text;
                itemSelectorHidden.value = value;
                selectorSearch.value = text;
                selectorDropdown.classList.add('hidden');
            });
        });
        
        // Filter selectors on input
        selectorSearch.addEventListener('input', () => {
            const searchTerm = selectorSearch.value.toLowerCase();
            selectorDropdown.querySelectorAll('.selector-option').forEach(option => {
                const text = option.dataset.text.toLowerCase();
                option.style.display = text.includes(searchTerm) ? 'block' : 'none';
            });
        });
    }

    // Filter seed list by selected portal (Edit)
    const editPortalHidden = document.getElementById('edit_portal');
    const editSeedList = document.getElementById('edit-seed-url-list');
    const editSeedSearch = document.getElementById('edit-seed-url-search');
    if (editPortalHidden && editSeedList) {
        editPortalHidden.addEventListener('change', () => {
            refreshSeedVisibility(editSeedList, editPortalHidden.value, editSeedSearch?.value, '.edit-seed-item');
            updateSeedUrlCount(editPortalHidden.value, 'edit-seed-url-count');
        });
        if (editSeedSearch) editSeedSearch.addEventListener('input', () => {
            refreshSeedVisibility(editSeedList, editPortalHidden.value, editSeedSearch.value, '.edit-seed-item');
            // Update count based on current portal selection
            if (editPortalHidden.value) {
                updateSeedUrlCount(editPortalHidden.value, 'edit-seed-url-count');
            }
        });
        refreshSeedVisibility(editSeedList, editPortalHidden.value, editSeedSearch?.value, '.edit-seed-item');
        
        // Initial count update
        updateSeedUrlCount(editPortalHidden.value, 'edit-seed-url-count');
    }
    
    // Handle portal search and dropdown for edit form
    const editPortalSearch = document.getElementById('edit-portal-search');
    const editPortalDropdown = document.getElementById('edit-portal-dropdown');
    
    if (editPortalSearch && editPortalDropdown && editPortalHidden) {
        // Show dropdown on focus
        editPortalSearch.addEventListener('focus', () => {
            editPortalDropdown.classList.remove('hidden');
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!editPortalSearch.contains(e.target) && !editPortalDropdown.contains(e.target)) {
                editPortalDropdown.classList.add('hidden');
            }
        });
        
        // Handle portal selection
        editPortalDropdown.querySelectorAll('.edit-portal-option').forEach(option => {
            option.addEventListener('click', () => {
                const value = option.dataset.value;
                const text = option.dataset.text;
                editPortalHidden.value = value;
                editPortalSearch.value = text;
                editPortalDropdown.classList.add('hidden');
                
                // Refresh seed visibility and update count
                if (editSeedList) {
                    refreshSeedVisibility(editSeedList, value, editSeedSearch?.value, '.edit-seed-item');
                    updateSeedUrlCount(value, 'edit-seed-url-count');
                }
            });
        });
        
        // Filter portals on input
        editPortalSearch.addEventListener('input', () => {
            const searchTerm = editPortalSearch.value.toLowerCase();
            editPortalDropdown.querySelectorAll('.edit-portal-option').forEach(option => {
                const text = option.dataset.text.toLowerCase();
                option.style.display = text.includes(searchTerm) ? 'block' : 'none';
            });
            
            // Update count based on current portal selection
            if (editPortalHidden.value) {
                updateSeedUrlCount(editPortalHidden.value, 'edit-seed-url-count');
            }
        });
    }
    
    // Handle item selector search and dropdown for edit form
    const editSelectorSearch = document.getElementById('edit-selector-search');
    const editSelectorDropdown = document.getElementById('edit-selector-dropdown');
    const editSelectorHidden = document.getElementById('edit_item_selector');
    
    if (editSelectorSearch && editSelectorDropdown && editSelectorHidden) {
        // Show dropdown on focus
        editSelectorSearch.addEventListener('focus', () => {
            editSelectorDropdown.classList.remove('hidden');
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!editSelectorSearch.contains(e.target) && !editSelectorDropdown.contains(e.target)) {
                editSelectorDropdown.classList.add('hidden');
            }
        });
        
        // Handle selector selection
        editSelectorDropdown.querySelectorAll('.edit-selector-option').forEach(option => {
            option.addEventListener('click', () => {
                const value = option.dataset.value;
                const text = option.dataset.text;
                editSelectorHidden.value = value;
                editSelectorSearch.value = text;
                editSelectorDropdown.classList.add('hidden');
            });
        });
        
        // Filter selectors on input
        editSelectorSearch.addEventListener('input', () => {
            const searchTerm = editSelectorSearch.value.toLowerCase();
            editSelectorDropdown.querySelectorAll('.edit-selector-option').forEach(option => {
                const text = option.dataset.text.toLowerCase();
                option.style.display = text.includes(searchTerm) ? 'block' : 'none';
            });
        });
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