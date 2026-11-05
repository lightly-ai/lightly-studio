// Query errors are typed as the API error body, which has no `message`, but can be an Error.
export const getErrorMessage = (error: unknown): string | undefined => {
    if (typeof error === 'object' && error !== null && 'message' in error) {
        return typeof error.message === 'string' ? error.message : undefined;
    }
    return undefined;
};
