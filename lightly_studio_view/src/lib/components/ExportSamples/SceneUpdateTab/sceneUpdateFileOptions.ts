// Only file name characters, matching the backend, so a suffix cannot add a folder.
const SUFFIX_PATTERN = /^[A-Za-z0-9_.-]*$/;

/** Returns whether a suffix has only file name characters. An empty suffix is valid. */
export function isValidSuffix(suffix: string): boolean {
    return SUFFIX_PATTERN.test(suffix);
}
