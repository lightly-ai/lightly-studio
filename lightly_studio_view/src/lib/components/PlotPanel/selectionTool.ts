export type ToolMode = 'pan' | 'rectangle' | 'lasso';

export interface ToolDescriptor {
    mode: ToolMode;
    label: string;
}

// The pill's three tools, in display order. Icons are mapped in the component so this
// module stays free of Svelte and can be unit-tested as plain logic.
export const SELECTION_TOOLS: readonly ToolDescriptor[] = [
    { mode: 'pan', label: 'Pan' },
    { mode: 'rectangle', label: 'Rectangle select' },
    { mode: 'lasso', label: 'Lasso select' }
];

// embedding-atlas marks the armed tool button with an inline `background: color-mix(...)`.
export function isButtonArmed(button: Element | null): boolean {
    return button?.getAttribute('style')?.includes('color-mix') ?? false;
}

// Resolve the library's rectangle/lasso buttons by their (stable, English) title text,
// falling back to DOM order if the wording ever changes.
export function findToolButtons(container: HTMLElement | null | undefined): {
    marquee: HTMLButtonElement | null;
    lasso: HTMLButtonElement | null;
} {
    const buttons = Array.from(
        container?.querySelectorAll<HTMLButtonElement>('.embedding-view button') ?? []
    );
    let marquee: HTMLButtonElement | null = null;
    let lasso: HTMLButtonElement | null = null;
    for (const button of buttons) {
        const title = button.getAttribute('title') ?? '';
        if (title.startsWith('Toggle rectangle selection')) marquee = button;
        else if (title.startsWith('Toggle lasso selection')) lasso = button;
    }
    // A partial rename would otherwise leave one tool dead, so fill each missing side from
    // DOM order separately, skipping whichever button the title match already claimed.
    if ((!marquee || !lasso) && buttons.length >= 2) {
        const unclaimed = buttons.filter((button) => button !== marquee && button !== lasso);
        marquee ??= unclaimed.shift() ?? null;
        lasso ??= unclaimed.shift() ?? null;
    }
    return { marquee, lasso };
}

// Which hidden library button (if any) must be clicked to bring the library's selection
// mode in line with the chosen tool. Pan is the library's "none" mode, so it disarms
// whichever tool is currently armed.
export function toolButtonToToggle(
    container: HTMLElement | null | undefined,
    activeTool: ToolMode
): HTMLButtonElement | null {
    const { marquee, lasso } = findToolButtons(container);
    if (activeTool === 'rectangle') return isButtonArmed(marquee) ? null : marquee;
    if (activeTool === 'lasso') return isButtonArmed(lasso) ? null : lasso;
    if (isButtonArmed(marquee)) return marquee;
    if (isButtonArmed(lasso)) return lasso;
    return null;
}

export interface SelectionToolController {
    // Re-assert the active tool onto the library's buttons. Safe to call repeatedly.
    reconcile: () => void;
    destroy: () => void;
}

// Owns the imperative glue that keeps the library's selection mode in sync with the pill:
// it watches the toolbar for (re)creation and for each button's inline-style flips (including
// the library's post-selection reset to "none") and re-clicks to keep the chosen tool sticky.
//
// `getActiveTool` is a getter, not a value, so callers can hand in reactive state without this
// module depending on Svelte. Clicking a hidden button changes the library's mode
// asynchronously, so a re-entrancy guard blocks a second click until the style observer
// confirms the change (or a short safety timeout elapses); otherwise DOM churn during the
// switch could click the same button again and toggle it straight back off.
export function createSelectionToolController(
    container: HTMLElement,
    getActiveTool: () => ToolMode
): SelectionToolController {
    let awaitingLibrary = false;
    let awaitingTimer: ReturnType<typeof setTimeout> | undefined;
    const observedButtons = new WeakSet<Element>();

    const reconcile = () => {
        if (awaitingLibrary) return;
        const button = toolButtonToToggle(container, getActiveTool());
        if (!button) return;
        awaitingLibrary = true;
        if (awaitingTimer) clearTimeout(awaitingTimer);
        awaitingTimer = setTimeout(() => {
            awaitingLibrary = false;
        }, 250);
        button.click();
    };

    const styleObserver = new MutationObserver(() => {
        // The mode actually changed, so a pending click has landed (or the library reset itself
        // after a selection). Clear the guard and reconcile: this is the sticky re-arm.
        awaitingLibrary = false;
        reconcile();
    });

    const observeButtons = () => {
        const { marquee, lasso } = findToolButtons(container);
        for (const button of [marquee, lasso]) {
            if (button && !observedButtons.has(button)) {
                observedButtons.add(button);
                // The library's strip is painted out (opacity 0) and replaced by the pill, so
                // take its buttons out of the tab order and the a11y tree — otherwise focus
                // lands on nothing visible and Enter arms a mode the pill does not show.
                // Neither attribute affects `.click()` or Playwright's visibility check.
                button.tabIndex = -1;
                button.setAttribute('aria-hidden', 'true');
                styleObserver.observe(button, { attributes: true, attributeFilter: ['style'] });
            }
        }
        reconcile();
    };

    const treeObserver = new MutationObserver(observeButtons);
    treeObserver.observe(container, { childList: true, subtree: true });
    observeButtons();

    return {
        reconcile,
        destroy: () => {
            treeObserver.disconnect();
            styleObserver.disconnect();
            if (awaitingTimer) clearTimeout(awaitingTimer);
            // Never leave the guard armed across a teardown, or the next controller would
            // ignore every reconcile.
            awaitingLibrary = false;
        }
    };
}
