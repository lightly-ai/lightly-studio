/** Asks for the source new annotations go to. Shown in the panel, on the canvas and in toasts. */
export const PICK_SOURCE_MESSAGE = 'Pick where new annotations go.';

/** What to tell the user while the source list loads. */
export const LOADING_SOURCES_MESSAGE = 'Loading annotation sources…';

/** What to tell the user when the source list did not load. */
export const SOURCES_ERROR_MESSAGE =
    'Could not load the annotation sources. Reload the page to add annotations.';

/** Why new annotations can't go to a hidden source. */
export const getHiddenSourceMessage = (sourceName: string): string =>
    `${sourceName} is hidden. Show it in the Annotations panel to add annotations to it.`;
