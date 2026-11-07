/** An HTTP error response from the API. */
export class ApiError extends Error {
    override readonly name = 'ApiError';

    constructor(
        message: string,
        readonly status: number,
        /** The `detail.type` of a structured error, such as `transform_unavailable`. */
        readonly type?: string
    ) {
        super(message);
    }

    /**
     * Creates an `ApiError` from the parsed body of an HTTP error response.
     *
     * FastAPI sends `detail` as text, as a list of validation errors, or as a `{ type, message }`
     * object. Some endpoints send an `error` text, and an unhandled error gives a plain text body.
     */
    static fromResponseBody(body: unknown, status: number): ApiError {
        const message = getBodyMessage(body) ?? `Request failed with status ${status}.`;
        const detail = isRecord(body) ? body.detail : undefined;
        return new ApiError(message, status, getStringField(detail, 'type'));
    }
}

/** Returns the message of an error, or `fallback` if the error is not an `Error`. */
export const getErrorMessage = (error: unknown, fallback: string): string =>
    error instanceof Error ? error.message : fallback;

const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null;

const getStringField = (value: unknown, field: string): string | undefined => {
    const fieldValue = isRecord(value) ? value[field] : undefined;
    return typeof fieldValue === 'string' ? fieldValue : undefined;
};

const getBodyMessage = (body: unknown): string | undefined => {
    if (typeof body === 'string') return body || undefined;
    if (!isRecord(body)) return undefined;
    if (typeof body.error === 'string') return body.error;
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return getStringField(body.detail[0], 'msg');
    return getStringField(body.detail, 'message');
};
