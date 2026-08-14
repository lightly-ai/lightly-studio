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

// Split the header wordmark two-tone, as on the landing page: "Lightly" in
// ink, "Studio" in grey. Falls back to tinting the trailing word for a site
// name that is several words rather than one CamelCase token.
function splitWordmark(name) {
    const words = name.split(/\s+/);
    if (words.length > 1) {
        return [words.slice(0, -1).join(' ') + ' ', words[words.length - 1]];
    }
    const camel = /^([A-Z][a-z]+)([A-Z].*)$/.exec(name);
    return camel ? [camel[1], camel[2]] : null;
}

function accentWordmarkTail() {
    const topic = document.querySelector('.md-header__title .md-header__topic .md-ellipsis');
    if (!topic || topic.querySelector('.ls-wordmark-accent')) return;

    const parts = splitWordmark(topic.textContent.trim());
    if (!parts) return;

    topic.textContent = parts[0];
    const accent = document.createElement('span');
    accent.className = 'ls-wordmark-accent';
    accent.textContent = parts[1];
    topic.appendChild(accent);
}

document.addEventListener('DOMContentLoaded', function () {
    addSearchShortcutHint();
    accentWordmarkTail();
});
