// Used when neither the selected class nor a hint gives a class name.
const FALLBACK_CLASS_NAME = 'object';

// The first non-blank candidate wins, e.g. the selected class before a hinted class.
export const pickClassName = (candidates: (string | null | undefined)[]): string =>
    candidates.map((candidate) => candidate?.trim()).find(Boolean) ?? FALLBACK_CLASS_NAME;

export const getAnnotationPreviewErrorMessage = (error: unknown): string => {
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
    return 'Unknown error';
};
