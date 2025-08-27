// static/assets/seed-urls.js

document.addEventListener('DOMContentLoaded', function () {
    // ----- Get Flowbite Drawer instances (create uses data- attrs; update/delete we open programmatically) -----
    const updateDrawerEl = document.getElementById('drawer-update-seed-url-default');
    const deleteDrawerEl = document.getElementById('drawer-delete-seed-url-default');
  
    // If Flowbite hasn't auto-instantiated, new Drawer(...) will instantiate it.
    // (Placement/backdrop come from data- attrs on the element)
    const updateDrawer = updateDrawerEl ? new Drawer(updateDrawerEl) : null;
    const deleteDrawer = deleteDrawerEl ? new Drawer(deleteDrawerEl) : null;
  
    // ----- Event delegation for Edit/Delete buttons -----
    document.addEventListener('click', function (e) {
      const updateBtn = e.target.closest('.updateSeedUrlButton');
      if (updateBtn && updateDrawer) {
        const row = updateBtn.closest('tr');
        const url = row.querySelector('[data-field="url"] a').textContent.trim();
        const portalEl = row.querySelector('[data-field="portal"]');
        const portalId = portalEl.getAttribute('data-portal-id');
        const portalName = portalEl.querySelector('.text-base').textContent.trim();
  
        // Fill the update form fields
        document.getElementById('update-url').value = url;
        document.getElementById('update-portal-search').value = portalName;
        document.getElementById('update-portal').value = portalId;
  
        const seedUrlId = row.getAttribute('data-seed-url-id');
        document.getElementById('updateSeedUrlForm').action = `/common/seed-urls/${seedUrlId}/edit/`;
  
        // Open the drawer
        updateDrawer.show();
      }
  
      const deleteBtn = e.target.closest('.deleteSeedUrlButton');
      if (deleteBtn && deleteDrawer) {
        const row = deleteBtn.closest('tr');
        const url = row.querySelector('[data-field="url"] a').textContent.trim();
        const portalName = row.querySelector('[data-field="portal"] .text-base').textContent.trim();
  
        document.getElementById('delete-url').textContent = url;
        document.getElementById('delete-portal').textContent = portalName;
  
        const seedUrlId = row.getAttribute('data-seed-url-id');
        document.getElementById('deleteSeedUrlForm').action = `/common/seed-urls/${seedUrlId}/delete/`;
  
        deleteDrawer.show();
      }
    });
  
    // ----- Simple portal dropdown filter (Create) -----
    attachPortalPicker({
      searchInputId: 'portal-search',
      hiddenInputId: 'portal',
      dropdownId: 'portal-dropdown',
      noResultsId: 'no-results'
    });
  
    // ----- Simple portal dropdown filter (Update) -----
    attachPortalPicker({
      searchInputId: 'update-portal-search',
      hiddenInputId: 'update-portal',
      dropdownId: 'update-portal-dropdown',
      noResultsId: 'update-no-results'
    });
  });
  
  /**
   * Lightweight dropdown filter/selector.
   * Expects .portal-option elements with data-value and data-text attributes.
   */
  function attachPortalPicker({ searchInputId, hiddenInputId, dropdownId, noResultsId }) {
    const search = document.getElementById(searchInputId);
    const hidden = document.getElementById(hiddenInputId);
    const dropdown = document.getElementById(dropdownId);
    if (!search || !hidden || !dropdown) return;
  
    const noResults = noResultsId ? document.getElementById(noResultsId) : null;
  
    search.addEventListener('focus', () => dropdown.classList.remove('hidden'));
  
    search.addEventListener('input', function () {
      const q = this.value.toLowerCase();
      const options = dropdown.querySelectorAll('.portal-option');
      let visible = 0;
      options.forEach(opt => {
        const text = (opt.getAttribute('data-text') || '').toLowerCase();
        const show = text.includes(q);
        opt.style.display = show ? 'block' : 'none';
        if (show) visible++;
      });
      if (noResults) noResults.classList.toggle('hidden', visible > 0);
      dropdown.classList.remove('hidden');
    });
  
    dropdown.addEventListener('click', function (e) {
      const option = e.target.closest('.portal-option');
      if (!option) return;
      const value = option.getAttribute('data-value');
      const text = option.getAttribute('data-text');
      search.value = text;
      hidden.value = value;
      dropdown.classList.add('hidden');
    });
  
    search.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !dropdown.classList.contains('hidden')) {
        e.preventDefault();
        const firstVisible = dropdown.querySelector('.portal-option[style*="block"], .portal-option:not([style*="none"])');
        if (firstVisible) {
          const value = firstVisible.getAttribute('data-value');
          const text = firstVisible.getAttribute('data-text');
          search.value = text;
          hidden.value = value;
          dropdown.classList.add('hidden');
        }
      } else if (e.key === 'Escape') {
        dropdown.classList.add('hidden');
        search.blur();
      }
    });
  
    document.addEventListener('click', function (e) {
      if (!search.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.add('hidden');
      }
    });
  }
  