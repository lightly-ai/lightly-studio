/** The backend default source new annotations land in when no name is sent. */
export const DEFAULT_SOURCE_NAME = 'annotation';

/**
 * Returns the source new annotations are written to. With several sources the user must pick
 * one, so nothing lands in a source by accident: null means "not picked yet". With one source
 * it is that one, and with none the backend default is created on the first annotation.
 */
export const resolveTargetSource = (
    chosenSource: string | null | undefined,
    sourceNames: string[]
): string | null => {
    if (chosenSource) return chosenSource;
    if (sourceNames.length === 0) return DEFAULT_SOURCE_NAME;
    if (sourceNames.length === 1) return sourceNames[0];
    return null;
};

/** What to do when no source is picked, for the pencil picker in the Annotations panel. */
export const PENCIL_PICK_MESSAGE =
    'Pick a source with the pencil in the Annotations panel before adding annotations.';

/**
 * Returns why new annotations must not be created, or null when they may. A hidden target is
 * blocked so nothing is added to a source the user can't see. `pickMessage` says how to pick a
 * source in the picker the user sees.
 */
export const getTargetBlockedReason = (
    targetSource: string | null,
    isTargetHidden: boolean,
    pickMessage: string = PENCIL_PICK_MESSAGE
): string | null => {
    if (targetSource === null) {
        return pickMessage;
    }
    if (isTargetHidden) {
        return `${targetSource} is hidden. Show it in the Annotations panel to add annotations to it.`;
    }
    return null;
};
