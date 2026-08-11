document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.md-search__input');
        if (searchInput) {
            searchInput.focus();
        }
    }
});

// Inject a ⌘K / Ctrl+K hint badge into the search form
function addSearchShortcutHint() {
    if (document.querySelector('.search-shortcut-hint')) return;
    const searchForm = document.querySelector('.md-search__form');
    if (!searchForm) return;

    const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
    const hint = document.createElement('div');
    hint.className = 'search-shortcut-hint';
    hint.innerHTML = isMac
        ? '<kbd>\u2318K</kbd>'
        : '<kbd>Ctrl+K</kbd>';
    searchForm.appendChild(hint);
}

document.addEventListener('DOMContentLoaded', addSearchShortcutHint);
