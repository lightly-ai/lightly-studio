document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.code === 'KeyK') {
        e.preventDefault();
        const searchToggle = document.querySelector('input[data-md-toggle="search"]');
        if (searchToggle && !searchToggle.checked) {
            searchToggle.checked = true;
            searchToggle.dispatchEvent(new Event('change'));
        }
        const searchInput = document.querySelector('.md-search__input');
        if (searchInput) {
            searchInput.focus();
        }
    }
});

function isMacPlatform() {
    if (navigator.userAgentData) {
        return navigator.userAgentData.platform === 'macOS';
    }
    return /Mac|iPhone|iPad|iPod/.test(navigator.userAgent);
}

// Inject a ⌘K / Ctrl+K hint badge into the search form
function addSearchShortcutHint() {
    if (document.querySelector('.search-shortcut-hint')) return;
    const searchForm = document.querySelector('.md-search__form');
    if (!searchForm) return;

    const hint = document.createElement('div');
    hint.className = 'search-shortcut-hint';
    hint.innerHTML = isMacPlatform()
        ? '<kbd>\u2318K</kbd>'
        : '<kbd>Ctrl+K</kbd>';
    searchForm.appendChild(hint);
}

document.addEventListener('DOMContentLoaded', addSearchShortcutHint);
