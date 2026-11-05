/**
 * Returns a message for an error from the API client, or `undefined` if there is no error.
 *
 * An HTTP error gives the parsed response body, for example `{ detail: 'Not found' }` or a
 * validation error with a `detail` list. A network failure gives an `Error`.
 */
export const getErrorMessage = (error: unknown): string | undefined => {
    if (error === null || error === undefined) return undefined;
    if (typeof error === 'object') {
        const body = error as { error?: unknown; detail?: unknown; message?: unknown };
        if (typeof body.error === 'string') return body.error;
        if (typeof body.detail === 'string') return body.detail;
        if (Array.isArray(body.detail)) {
            const msg = (body.detail[0] as { msg?: unknown } | undefined)?.msg;
            if (typeof msg === 'string') return msg;
        }
        if (typeof body.message === 'string' && body.message) return body.message;
    }
    return 'Unknown error';
};
