// Search-based dropdown functionality
class SearchDropdown {
    constructor(searchInputId, dropdownId, hiddenInputId, optionsSelector) {
        this.searchInput = document.getElementById(searchInputId);
        this.dropdown = document.getElementById(dropdownId);
        this.hiddenInput = document.getElementById(hiddenInputId);
        this.optionsSelector = optionsSelector;
        
        if (!this.searchInput || !this.dropdown || !this.hiddenInput) {
            console.warn('SearchDropdown: Required elements not found', { searchInputId, dropdownId, hiddenInputId });
            return;
        }
        
        this.options = this.dropdown.querySelectorAll(optionsSelector);
        this.selectedOption = null;
        
        this.init();
    }
    
    init() {
        // Show dropdown on focus
        this.searchInput.addEventListener('focus', () => {
            this.showDropdown();
        });
        
        // Handle search input
        this.searchInput.addEventListener('input', (e) => {
            this.filterOptions(e.target.value);
        });
        
        // Handle option selection
        this.dropdown.addEventListener('click', (e) => {
            const option = e.target.closest(this.optionsSelector);
            if (option) {
                this.selectOption(option);
            }
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.hideDropdown();
            }
        });
        
        // Handle keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });
        
        // Clear search when hidden input changes
        this.hiddenInput.addEventListener('change', () => {
            if (!this.hiddenInput.value) {
                this.searchInput.value = '';
            }
        });
    }
    
    filterOptions(searchTerm) {
        const term = searchTerm.toLowerCase();
        let hasVisibleOptions = false;
        
        this.options.forEach(option => {
            const text = option.getAttribute('data-text').toLowerCase();
            const isVisible = text.includes(term);
            
            option.style.display = isVisible ? 'block' : 'none';
            if (isVisible) hasVisibleOptions = true;
        });
        
        if (hasVisibleOptions && searchTerm.length > 0) {
            this.showDropdown();
        } else if (searchTerm.length === 0) {
            // Show all options when search is empty
            this.options.forEach(option => {
                option.style.display = 'block';
            });
            this.showDropdown();
        } else {
            this.hideDropdown();
        }
    }
    
    selectOption(option) {
        const value = option.getAttribute('data-value');
        const text = option.getAttribute('data-text');
        
        this.hiddenInput.value = value;
        this.searchInput.value = text;
        this.selectedOption = option;
        
        this.hideDropdown();
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        this.hiddenInput.dispatchEvent(event);
    }
    
    showDropdown() {
        this.dropdown.classList.remove('hidden');
        // Ensure dropdown is above other elements
        this.dropdown.style.zIndex = '9999';
    }
    
    hideDropdown() {
        this.dropdown.classList.add('hidden');
    }
    
    handleKeyboardNavigation(e) {
        const visibleOptions = Array.from(this.options).filter(option => 
            option.style.display !== 'none'
        );
        
        let currentIndex = visibleOptions.indexOf(this.selectedOption);
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                currentIndex = Math.min(currentIndex + 1, visibleOptions.length - 1);
                this.highlightOption(visibleOptions[currentIndex]);
                break;
            case 'ArrowUp':
                e.preventDefault();
                currentIndex = Math.max(currentIndex - 1, 0);
                this.highlightOption(visibleOptions[currentIndex]);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedOption) {
                    this.selectOption(this.selectedOption);
                }
                break;
            case 'Escape':
                this.hideDropdown();
                this.searchInput.blur();
                break;
        }
    }
    
    highlightOption(option) {
        // Remove previous highlights
        this.options.forEach(opt => opt.classList.remove('bg-primary-100', 'dark:bg-primary-700'));
        
        // Add highlight to current option
        if (option) {
            option.classList.add('bg-primary-100', 'dark:bg-primary-700');
            this.selectedOption = option;
            
            // Scroll to option if needed
            option.scrollIntoView({ block: 'nearest' });
        }
    }
}

// Initialize search dropdowns when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize portal search dropdowns (create form)
    const portalSearch = document.getElementById('portal-search');
    if (portalSearch) {
        new SearchDropdown('portal-search', 'portal-dropdown', 'portal', '.portal-option');
    }
    
    // Initialize selector search dropdowns (create form)
    const selectorSearch = document.getElementById('selector-search');
    if (selectorSearch) {
        new SearchDropdown('selector-search', 'selector-dropdown', 'item_selector', '.selector-option');
    }
    
    // Initialize edit portal search dropdowns (crawler configs)
    const editPortalSearch = document.getElementById('edit-portal-search');
    if (editPortalSearch) {
        new SearchDropdown('edit-portal-search', 'edit-portal-dropdown', 'edit_portal', '.edit-portal-option');
    }
    
    // Initialize edit selector search dropdowns (crawler configs)
    const editSelectorSearch = document.getElementById('edit-selector-search');
    if (editSelectorSearch) {
        new SearchDropdown('edit-selector-search', 'edit-selector-dropdown', 'edit_item_selector', '.edit-selector-option');
    }
    
    // Initialize edit portal search dropdowns (selectors)
    const editPortalSearchSelectors = document.getElementById('edit-portal-search-selectors');
    if (editPortalSearchSelectors) {
        new SearchDropdown('edit-portal-search-selectors', 'edit-portal-dropdown-selectors', 'edit_portal', '.edit-portal-option-selectors');
    }
}); 