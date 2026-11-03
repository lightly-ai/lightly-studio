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

/**
 * Returns why new annotations must not be created, or null when they may. A hidden target is
 * blocked so nothing is added to a source the user can't see.
 */
export const getTargetBlockedReason = (
    targetSource: string | null,
    isTargetHidden: boolean
): string | null => {
    if (targetSource === null) {
        return 'Pick a source with the pencil in the Annotations panel before adding annotations.';
    }
    if (isTargetHidden) {
        return `${targetSource} is hidden. Show it in the Annotations panel to add annotations to it.`;
    }
    return null;
};
