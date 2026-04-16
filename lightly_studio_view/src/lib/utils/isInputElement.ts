/**
 * Checks if the event target is an input element where keyboard shortcuts should be disabled.
 * Covers standard inputs, contenteditable elements, and Monaco editor (which uses an internal
 * div with tabindex as its keyboard target, not a textarea or contenteditable).
 */
export const isInputElement = (target: EventTarget | null): boolean => {
    if (!(target instanceof HTMLElement)) return false;
    return (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target.isContentEditable ||
        target.closest('.monaco-editor') !== null
    );
};
