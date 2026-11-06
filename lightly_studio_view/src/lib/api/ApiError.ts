/** An HTTP error response from the API. */
export class ApiError extends Error {
    override readonly name = 'ApiError';

    constructor(
        message: string,
        readonly status: number
    ) {
        super(message);
    }

    /**
     * Creates an `ApiError` from the parsed body of an HTTP error response.
     *
     * FastAPI sends `detail` as text, or as a list of validation errors. Some endpoints send an
     * `error` text, and an unhandled error gives a plain text body.
     */
    static fromResponseBody(body: unknown, status: number): ApiError {
        const message = getBodyMessage(body) ?? `Request failed with status ${status}.`;
        return new ApiError(message, status);
    }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null;

const getBodyMessage = (body: unknown): string | undefined => {
    if (typeof body === 'string') return body || undefined;
    if (!isRecord(body)) return undefined;
    if (typeof body.error === 'string') return body.error;
    if (typeof body.detail === 'string') return body.detail;
    return getValidationMessage(body.detail);
};

const getValidationMessage = (detail: unknown): string | undefined => {
    const firstError: unknown = Array.isArray(detail) ? detail[0] : undefined;
    return isRecord(firstError) && typeof firstError.msg === 'string' ? firstError.msg : undefined;
};
