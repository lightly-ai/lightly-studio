interface Snapshot {
    focused: HTMLElement;
    row: HTMLElement | null;
    top: number;
    innerScroll: [HTMLElement, number][];
}

/**
 * Keeps the row you work in where it is when `getOrder()` moves it.
 *
 * Before the update it records the focused element, the screen position of its row and the
 * scroll positions inside the row. After the update it restores focus, scrolls the nearest
 * scrollable ancestor so the row is at the same screen position, and restores the inner
 * scroll positions. Moving a node in a keyed `{#each}` can blur it and reset its scroll.
 * Nothing happens while the order stays the same.
 */
export function keepFocusOnMove(
    getContainer: () => HTMLElement | undefined,
    getOrder: () => string[]
): void {
    let previousKey = getOrder().join('\0');
    let snapshot: Snapshot | undefined;

    $effect.pre(() => {
        const key = getOrder().join('\0');
        const moved = key !== previousKey;
        previousKey = key;
        const active = document.activeElement;
        snapshot =
            moved && active instanceof HTMLElement && getContainer()?.contains(active)
                ? takeSnapshot(active)
                : undefined;
    });

    $effect(() => {
        getOrder();
        const saved = snapshot;
        snapshot = undefined;
        if (!saved?.focused.isConnected) return;
        if (document.activeElement !== saved.focused) saved.focused.focus({ preventScroll: true });
        for (const [element, scrollTop] of saved.innerScroll) element.scrollTop = scrollTop;
        if (!saved.row) return;
        const scroller = findScrollParent(saved.row);
        if (scroller) scroller.scrollTop += saved.row.getBoundingClientRect().top - saved.top;
    });
}

const takeSnapshot = (focused: HTMLElement): Snapshot => {
    const row = focused.closest<HTMLElement>('[data-field-id]');
    const inner = row ? [...row.querySelectorAll<HTMLElement>('*')] : [];
    return {
        focused,
        row,
        top: row?.getBoundingClientRect().top ?? 0,
        innerScroll: inner
            .filter((element) => element.scrollTop > 0)
            .map((element) => [element, element.scrollTop])
    };
};

const findScrollParent = (element: HTMLElement): HTMLElement | null => {
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
        const { overflowY } = getComputedStyle(parent);
        if (overflowY === 'auto' || overflowY === 'scroll') return parent;
    }
    return null;
};
