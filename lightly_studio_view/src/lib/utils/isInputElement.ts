/**
 * Checks if the event target is an input element where keyboard shortcuts should be disabled.
 */
export const isInputElement = (target: EventTarget | null): boolean => {
    return (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement
    );
};
