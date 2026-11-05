import { isOverlayTarget } from './isOverlayTarget';
import { isTextInputTarget } from './isTextInputTarget';

type KeyPress = Pick<KeyboardEvent, 'key' | 'target' | 'repeat' | 'altKey' | 'ctrlKey' | 'metaKey'>;

const isPlainPress = (event: KeyPress) =>
    !event.repeat &&
    !event.altKey &&
    !event.ctrlKey &&
    !event.metaKey &&
    !isTextInputTarget(event.target) &&
    !isOverlayTarget(event.target);

/** Whether a key press should delete the selected annotation. */
export const isDeleteKey = (event: KeyPress): boolean =>
    (event.key === 'Delete' || event.key === 'Backspace') && isPlainPress(event);

const CARD_BUTTON = ['button', 'a', '[role="button"]']
    .map((control) => `[data-annotation-card] ${control}`)
    .join(', ');

const isCardButtonTarget = (target: EventTarget | null) =>
    target instanceof Element && target.closest(CARD_BUTTON) !== null;

/**
 * Whether a key press should open the class search of the selected annotation.
 *
 * Enter, not letters, so the single-letter tool shortcuts keep working. A focused button on the
 * annotation card keeps Enter for its own click.
 */
export const isRelabelKey = (event: KeyPress): boolean =>
    event.key === 'Enter' && isPlainPress(event) && !isCardButtonTarget(event.target);
