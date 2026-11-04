/**
 * Returns the `message` of an error, if it has one.
 *
 * Query errors are typed as API error bodies, but a failed request can also throw an
 * `Error`, for example on a network failure. Values without a string `message` give
 * `undefined`.
 */
export const getErrorMessage = (error: unknown): string | undefined =>
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof error.message === 'string'
        ? error.message
        : undefined;
