/**
 * The message of an API error, for a toast: the `error` or `detail` of the response body, the
 * first message of a validation error, or the message of a thrown Error. `fallback` when the
 * error says nothing usable.
 */
export const getApiErrorMessage = (error: unknown, fallback = 'Unknown error'): string => {
    if (error && typeof error === 'object') {
        const body = error as { error?: unknown; detail?: unknown };
        if (typeof body.error === 'string') return body.error;
        if (typeof body.detail === 'string') return body.detail;
        if (Array.isArray(body.detail)) {
            const msg = (body.detail[0] as { msg?: unknown } | undefined)?.msg;
            if (typeof msg === 'string') return msg;
        }
    }
    if (error instanceof Error && error.message) return error.message;
    return fallback;
};
