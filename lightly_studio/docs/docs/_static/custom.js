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

// Instant navigation replaces `[data-md-component=container]`, which the header
// sits outside of — so the header copy of the section tabs still marks whichever
// tab was active when the page was first loaded. The drawer copy is inside that
// region and is re-rendered per page, so it is the one telling the truth; copy
// its state across after every navigation.
function syncSectionTabs() {
    const source = document.querySelector('.ls-tabs--drawer .ls-tabs__link--active');
    const activeTab = source ? source.dataset.lsTab : null;

    document.querySelectorAll('.ls-tabs--header .ls-tabs__link').forEach(function (link) {
        const isActive = link.dataset.lsTab === activeTab;
        link.classList.toggle('ls-tabs__link--active', isActive);
        if (isActive) {
            link.setAttribute('aria-current', source.getAttribute('aria-current') || 'true');
        } else {
            link.removeAttribute('aria-current');
        }
    });
}

document.addEventListener('DOMContentLoaded', addSearchShortcutHint);

// `navigation.instant` swaps the article without a page load, so the header copy
// of the strip has to be re-synced per navigation. `document$` is Material's
// observable for exactly that.
document$.subscribe(syncSectionTabs);
