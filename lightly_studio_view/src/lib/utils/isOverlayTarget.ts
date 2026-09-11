/**
 * Checks if an event target is inside an overlay (dialog, menu, listbox, popover)
 * where window-level keyboard shortcuts should be ignored.
 */
export const isOverlayTarget = (target: EventTarget | null): boolean =>
    target instanceof Element &&
    target.closest('[role="dialog"], [role="menu"], [role="listbox"], [data-popover-content]') !==
        null;
