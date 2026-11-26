// Controls that use Space themselves, so Space on them must not toggle playback.
const SPACE_CONTROLS =
    'button, input, select, textarea, [role="button"], [role="slider"], [role="switch"], [contenteditable="true"]';

/** Whether a keydown in the camera dialog is a Space press that toggles playback. */
export function isPlaybackSpace(event: KeyboardEvent): boolean {
    if (event.code !== 'Space' || event.repeat) return false;
    return !(event.target as HTMLElement).closest(SPACE_CONTROLS);
}
