/**
 * Full-page navigation to the given URL.
 *
 * This is a thin wrapper around `window.location` so callers can be tested by spying
 * on this function instead of stubbing `window.location`.
 *
 * @param url - The URL to navigate to.
 */
export const redirectTo = (url: string): void => {
    window.location.href = url;
};
