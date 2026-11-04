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
 * The source to seed when the user has not picked one yet, or null to leave it unpicked. A
 * default that no longer exists (deleted) is ignored, so the user must pick.
 */
export const pickInitialSource = ({
    chosenSource,
    sourceNames,
    defaultSource
}: {
    chosenSource: string | null | undefined;
    sourceNames: string[];
    defaultSource: string | undefined;
}): string | null => {
    if (chosenSource) return null;
    if (defaultSource && sourceNames.includes(defaultSource)) return defaultSource;
    return sourceNames.length === 1 ? sourceNames[0] : null;
};

/** What to tell the user when no source is picked. */
export const PICK_SOURCE_MESSAGE =
    'Choose where new annotations go: pick a source in the Annotations panel.';

/**
 * Returns why new annotations must not be created, or null when they may. A hidden target is
 * blocked so nothing is added to a source the user can't see. `pickMessage` says how to pick a
 * source in the picker the user sees.
 */
export const getTargetBlockedReason = (
    targetSource: string | null,
    isTargetHidden: boolean,
    pickMessage: string = PICK_SOURCE_MESSAGE
): string | null => {
    if (targetSource === null) {
        return pickMessage;
    }
    if (isTargetHidden) {
        return `${targetSource} is hidden. Show it in the Annotations panel to add annotations to it.`;
    }
    return null;
};
