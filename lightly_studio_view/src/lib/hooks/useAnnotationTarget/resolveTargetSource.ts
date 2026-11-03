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
