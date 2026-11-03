import { describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import {
    isAnnotationSourceMissing,
    MISSING_ANNOTATION_SOURCE_MESSAGE
} from './annotationSourceGuard';

vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

describe('isAnnotationSourceMissing', () => {
    it('blocks and explains when no source is picked among several', () => {
        expect(isAnnotationSourceMissing({ annotationSourceMissing: true })).toBe(true);
        expect(toast.error).toHaveBeenCalledWith(MISSING_ANNOTATION_SOURCE_MESSAGE);
    });

    it('lets the annotation through when a source is set', () => {
        vi.mocked(toast.error).mockClear();

        expect(isAnnotationSourceMissing({ annotationSourceMissing: false })).toBe(false);
        expect(isAnnotationSourceMissing({})).toBe(false);
        expect(toast.error).not.toHaveBeenCalled();
    });
});
