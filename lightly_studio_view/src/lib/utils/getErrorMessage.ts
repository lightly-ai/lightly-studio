/**
 * Returns a message for an error from the API client, or `undefined` if it has none.
 *
 * An HTTP error gives the parsed response body, for example `{ detail: 'Not found' }` or a
 * validation error with a `detail` list. A transport failure gives an `Error`.
 */
export const getErrorMessage = (error: unknown): string | undefined => {
    if (typeof error !== 'object' || error === null) return undefined;
    const body = error as { error?: unknown; detail?: unknown; message?: unknown };
    if (typeof body.error === 'string') return body.error;
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) {
        const msg = (body.detail[0] as { msg?: unknown } | undefined)?.msg;
        if (typeof msg === 'string') return msg;
    }
    if (typeof body.message === 'string') return body.message;
    return undefined;
};
