import { describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import { isAnnotationSourceBlocked } from './annotationSourceGuard';

vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

describe('isAnnotationSourceBlocked', () => {
    it('blocks and shows the reason', () => {
        expect(isAnnotationSourceBlocked({ annotationSourceBlockedReason: 'Pick a source.' })).toBe(
            true
        );
        expect(toast.error).toHaveBeenCalledWith('Pick a source.');
    });

    it('lets the annotation through without a reason', () => {
        vi.mocked(toast.error).mockClear();

        expect(isAnnotationSourceBlocked({ annotationSourceBlockedReason: null })).toBe(false);
        expect(isAnnotationSourceBlocked({})).toBe(false);
        expect(toast.error).not.toHaveBeenCalled();
    });
});
