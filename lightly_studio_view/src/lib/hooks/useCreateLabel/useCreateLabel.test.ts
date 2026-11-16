import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMutation } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { useCanCreateAnnotationClass } from '$lib/hooks/useCanCreateAnnotationClass/useCanCreateAnnotationClass';
import {
    AnnotationClassNotAvailableError,
    getCreateLabelErrorMessage,
    useCreateLabel
} from './useCreateLabel';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, createMutation: vi.fn() };
});

vi.mock('$lib/hooks/useCanCreateAnnotationClass/useCanCreateAnnotationClass', () => ({
    useCanCreateAnnotationClass: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: { error: vi.fn() }
}));

describe('useCreateLabel', () => {
    const label = { annotation_label_id: 'l1', annotation_label_name: 'cat' };
    const mutate = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        mutate.mockImplementation((_vars: unknown, opts: { onSuccess: (data: unknown) => void }) =>
            opts.onSuccess(label)
        );
        vi.mocked(createMutation).mockReturnValue({
            mutate
        } as unknown as ReturnType<typeof createMutation>);
    });

    it('rejects without a request below editor', async () => {
        vi.mocked(useCanCreateAnnotationClass).mockReturnValue(false);

        const { createLabel, canCreateLabel } = useCreateLabel({ getCollectionId: () => 'c1' });
        const result = createLabel({ dataset_id: 'd', annotation_label_name: 'cat' });

        await expect(result).rejects.toBeInstanceOf(AnnotationClassNotAvailableError);
        await expect(result).rejects.toThrow(
            'Class "cat" is no longer available. Choose another class.'
        );
        expect(mutate).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
        expect(canCreateLabel).toBe(false);
    });

    it('creates the class for editors', async () => {
        vi.mocked(useCanCreateAnnotationClass).mockReturnValue(true);
        const body = { dataset_id: 'd', annotation_label_name: 'cat' };

        const { createLabel, canCreateLabel } = useCreateLabel({ getCollectionId: () => 'c1' });

        await expect(createLabel(body)).resolves.toEqual(label);
        expect(mutate).toHaveBeenCalledWith(
            { path: { collection_id: 'c1' }, body },
            expect.anything()
        );
        expect(canCreateLabel).toBe(true);
    });
});

describe('getCreateLabelErrorMessage', () => {
    it('returns the error text for a class that is not available', () => {
        expect(
            getCreateLabelErrorMessage(new AnnotationClassNotAvailableError('cat'), 'fallback')
        ).toBe('Class "cat" is no longer available. Choose another class.');
    });

    it('returns the fallback for other errors', () => {
        expect(getCreateLabelErrorMessage(new Error('x'), 'fallback')).toBe('fallback');
    });
});
