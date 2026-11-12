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

/** Returns the message of an error, or `fallback` if the error has no message. */
export const getErrorMessage = (error: unknown, fallback: string): string =>
    (error instanceof Error && error.message) || fallback;

const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null;

const getStringField = (value: unknown, field: string): string | undefined => {
    const fieldValue = isRecord(value) ? value[field] : undefined;
    return getText(fieldValue);
};

const getText = (value: unknown): string | undefined =>
    typeof value === 'string' && value ? value : undefined;

const getBodyMessage = (body: unknown): string | undefined => {
    if (!isRecord(body)) return getText(body);
    const detail = Array.isArray(body.detail) ? body.detail[0] : body.detail;
    return (
        getText(body.error) ??
        getText(body.detail) ??
        getStringField(detail, 'msg') ??
        getStringField(detail, 'message')
    );
};
