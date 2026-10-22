// Used when neither the selected class nor a hint gives a class name.
const FALLBACK_CLASS_NAME = 'object';

// A selected class wins as is, even with a blank name. A blank hint falls back.
export const pickClassName = ({
    selected,
    hint
}: {
    selected: string | null | undefined;
    hint: string | null | undefined;
}): string => selected ?? (hint?.trim() || FALLBACK_CLASS_NAME);

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
