import { isTextInputTarget } from '$lib/utils/isTextInputTarget';

export type CameraDirection = 'previous' | 'next';

interface CameraKeys {
    previous: string;
    next: string;
}

const MIN_CAMERAS_TO_SWITCH = 2;
const DIGIT_KEY_PATTERN = /^[1-9]$/;

function hasAnyModifier(event: KeyboardEvent): boolean {
    return event.altKey || event.ctrlKey || event.metaKey || event.shiftKey;
}

// Many layouts type `[` and `]` with AltGr, which Windows reports as Ctrl + Alt.
function hasCommandModifier(event: KeyboardEvent): boolean {
    const isCtrlOrMeta = event.ctrlKey || event.metaKey;
    return isCtrlOrMeta && !event.getModifierState('AltGraph');
}

export function getAdjacentCamera(
    names: readonly string[],
    current: string,
    direction: CameraDirection
): string | undefined {
    const currentIndex = names.indexOf(current);
    if (names.length < MIN_CAMERAS_TO_SWITCH || currentIndex === -1) return undefined;

    const step = direction === 'next' ? 1 : -1;
    return names[(currentIndex + step + names.length) % names.length];
}

export function getCameraKeyAction(
    event: KeyboardEvent,
    keys: CameraKeys
): CameraDirection | undefined {
    if (isTextInputTarget(event.target) || hasCommandModifier(event)) return undefined;

    const key = event.key.toLowerCase();
    if (key === keys.previous.toLowerCase()) return 'previous';
    if (key === keys.next.toLowerCase()) return 'next';
    return undefined;
}

export function getCameraForDigit(
    event: KeyboardEvent,
    names: readonly string[]
): string | undefined {
    if (isTextInputTarget(event.target) || hasAnyModifier(event)) return undefined;
    if (!DIGIT_KEY_PATTERN.test(event.key)) return undefined;
    return names[Number(event.key) - 1];
}
