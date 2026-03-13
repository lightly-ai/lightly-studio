/**
 * Checks if an event target is a text-editable element where keyboard shortcuts should be ignored.
 */
export const isTextInputTarget = (target: EventTarget | null): boolean => {
    if (!(target instanceof HTMLElement)) return false;

    const isContentEditable =
        target.isContentEditable === true || target.contentEditable === 'true';

    return target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || isContentEditable;
};
