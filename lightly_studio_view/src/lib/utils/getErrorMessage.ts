import type { ValidationError } from '$lib/api/lightly_studio_local';

/**
 * The response body of an HTTP error. FastAPI sends a `detail` list for a validation error and a
 * `detail` text for other errors. Some endpoints send an `error` text.
 */
interface ApiErrorBody {
    detail?: string | ValidationError[];
    error?: string;
}

/**
 * Returns a message for an error from the API client, or `undefined` if it has none.
 *
 * An HTTP error gives the parsed response body. A transport failure gives an `Error`.
 */
export const getErrorMessage = (
    error: ApiErrorBody | Error | null | undefined
): string | undefined => {
    if (!error) return undefined;
    if (error instanceof Error) return error.message;
    if (error.error) return error.error;
    if (typeof error.detail === 'string') return error.detail;
    return error.detail?.[0]?.msg;
};
