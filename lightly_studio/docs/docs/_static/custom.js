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

// What a fence language is called in the header bar. Anything missing here is
// printed as written, so a new language needs an entry only when the tag and
// the name differ. `mysql` is the Pygments lexer the query-language pages
// borrow for highlighting; it is not SQL.
const CODE_LABELS = {
    py: 'python',
    bash: 'terminal',
    shell: 'terminal',
    console: 'terminal',
    powershell: 'terminal',
    mysql: 'lightly query language',
};

// Fill the header bar that `.md-typeset .highlight::before` renders: the
// `title=` on the fence if there is one, the language otherwise.
function labelCodeBlocks() {
    document.querySelectorAll('.md-typeset .highlight').forEach(function (block) {
        const filename = block.querySelector('span.filename');
        if (filename) {
            block.setAttribute('data-code-label', filename.textContent.trim());
            return;
        }
        const languageClass = Array.from(block.classList).find(function (name) {
            return name.startsWith('language-');
        });
        const language = languageClass ? languageClass.slice('language-'.length) : '';
        block.setAttribute('data-code-label', CODE_LABELS[language] || language || 'code');
    });
}

document.addEventListener('DOMContentLoaded', function () {
    addSearchShortcutHint();
    accentWordmarkTail();
});

// `navigation.instant` swaps the article without a page load, so anything that
// decorates article content — or that reads it, as the tab sync does — has to
// run per navigation rather than once on DOMContentLoaded. `document$` is
// Material's observable for exactly that.
document$.subscribe(labelCodeBlocks);
document$.subscribe(syncSectionTabs);
