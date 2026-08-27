import { isInputElement } from '$lib/utils';

/** Ctrl/Cmd+A, the grid's select-all shortcut. */
export const isSelectAllShortcut = (event: KeyboardEvent): boolean =>
    event.key === 'a' && (event.ctrlKey || event.metaKey);

/**
 * Whether the event target owns the shortcut itself. Text entry keeps Ctrl/Cmd+A
 * for selecting its own content, so the grid must not steal it there.
 */
export const isEditableTarget = (target: EventTarget | null): boolean =>
    isInputElement(target) || Boolean((target as HTMLElement | null)?.isContentEditable);
