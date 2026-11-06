import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useDeleteAnnotationSource } from './useDeleteAnnotationSource.svelte';

const mocks = vi.hoisted(() => ({
    mutate: vi.fn(),
    invalidate: vi.fn(),
    onDeleted: vi.fn(),
    onSuccess: undefined as undefined | (() => void),
    onError: undefined as undefined | ((error: unknown) => void),
    toastError: vi.fn()
}));

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    createMutation: (
        getOptions: () => { onSuccess: () => void; onError: (error: unknown) => void }
    ) => {
        mocks.onSuccess = getOptions().onSuccess;
        mocks.onError = getOptions().onError;
        return { mutate: mocks.mutate, isPending: false };
    }
}));
vi.mock('$lib/hooks/useInvalidateAnnotationSourceQueries', () => ({
    useInvalidateAnnotationSourceQueries: () => mocks.invalidate
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: mocks.toastError } }));

const setup = (name: string) =>
    useDeleteAnnotationSource(() => ({
        collectionId: 'col-1',
        source: { id: 's1', name },
        onDeleted: mocks.onDeleted
    }));

describe('useDeleteAnnotationSource', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useGlobalStorage().lastAnnotationSource.set({});
    });

    it('deletes the source of the owner collection', () => {
        setup('predictions').remove();

        expect(mocks.mutate).toHaveBeenCalledWith({
            path: { collection_id: 'col-1', annotation_collection_id: 's1' }
        });
    });

    it('forgets the deleted source as target, and refreshes', () => {
        const { lastAnnotationSource, updateLastAnnotationSource } = useGlobalStorage();
        updateLastAnnotationSource('col-1', 'predictions');
        setup('predictions');

        mocks.onSuccess?.();

        expect(get(lastAnnotationSource)['col-1']).toBeUndefined();
        expect(mocks.invalidate).toHaveBeenCalledWith('col-1');
        expect(mocks.onDeleted).toHaveBeenCalledOnce();
    });

    it('keeps another source as target', () => {
        const { lastAnnotationSource, updateLastAnnotationSource } = useGlobalStorage();
        updateLastAnnotationSource('col-1', 'labels');
        setup('predictions');

        mocks.onSuccess?.();

        expect(get(lastAnnotationSource)['col-1']).toBe('labels');
    });

    it('shows why the API refused the delete', () => {
        const message =
            "The annotation source 'predictions' is used by the evaluation runs run_1. Delete " +
            'these evaluation runs first.';
        setup('predictions');

        mocks.onError?.({ error: message });

        expect(mocks.toastError).toHaveBeenCalledWith(message);
        expect(mocks.onDeleted).not.toHaveBeenCalled();
    });
});
