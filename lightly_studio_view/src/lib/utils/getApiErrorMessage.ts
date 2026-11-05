/**
 * The message of an API error, for a toast: the `error` or `detail` of the response body, the
 * first message of a validation error, or the message of a thrown Error. `fallback` when the
 * error says nothing usable.
 */
export const getApiErrorMessage = (error: unknown, fallback = 'Unknown error'): string => {
    const body = (error && typeof error === 'object' ? error : {}) as {
        error?: unknown;
        detail?: unknown;
    };
    const validationError = Array.isArray(body.detail)
        ? (body.detail[0] as { msg?: unknown } | undefined)
        : undefined;
    const candidates = [
        body.error,
        body.detail,
        validationError?.msg,
        error instanceof Error ? error.message : undefined
    ];
    return candidates.find(isNonEmptyString) ?? fallback;
};

const isNonEmptyString = (value: unknown): value is string =>
    typeof value === 'string' && value.length > 0;
