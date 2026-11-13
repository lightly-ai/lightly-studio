import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useDeleteAnnotationSource } from './useDeleteAnnotationSource.svelte';

const mocks = vi.hoisted(() => ({
    mutate: vi.fn(),
    invalidate: vi.fn(),
    onDeleted: vi.fn(),
    onSuccess: undefined as undefined | (() => void | Promise<void>),
    onError: undefined as undefined | ((error: unknown) => void),
    toastError: vi.fn()
}));

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    createMutation: (
        getOptions: () => {
            onSuccess: () => void | Promise<void>;
            onError: (error: unknown) => void;
        }
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

    it('forgets the deleted source as target, and refreshes', async () => {
        const { lastAnnotationSource, updateLastAnnotationSource } = useGlobalStorage();
        updateLastAnnotationSource('col-1', 'predictions');
        setup('predictions').remove();

        await mocks.onSuccess?.();

        expect(get(lastAnnotationSource)['col-1']).toBeUndefined();
        expect(mocks.invalidate).toHaveBeenCalledWith('col-1');
        expect(mocks.onDeleted).toHaveBeenCalledOnce();
    });

    it('refreshes only once the navigation off the deleted source is done', async () => {
        const order: string[] = [];
        let finishNavigation = () => {};
        mocks.onDeleted.mockImplementationOnce(
            () =>
                new Promise<void>((resolve) => {
                    order.push('navigate');
                    finishNavigation = resolve;
                })
        );
        mocks.invalidate.mockImplementationOnce(() => order.push('invalidate'));
        setup('predictions').remove();

        const done = mocks.onSuccess?.();
        expect(order).toEqual(['navigate']);

        finishNavigation();
        await done;

        expect(order).toEqual(['navigate', 'invalidate']);
    });

    it('keeps another source as target', async () => {
        const { lastAnnotationSource, updateLastAnnotationSource } = useGlobalStorage();
        updateLastAnnotationSource('col-1', 'labels');
        setup('predictions').remove();

        await mocks.onSuccess?.();

        expect(get(lastAnnotationSource)['col-1']).toBe('labels');
    });

    it('cleans up the collection of the request when the params change before it ends', async () => {
        const { lastAnnotationSource, updateLastAnnotationSource } = useGlobalStorage();
        updateLastAnnotationSource('col-1', 'predictions');
        updateLastAnnotationSource('col-2', 'predictions');
        let collectionId = 'col-1';
        const { remove } = useDeleteAnnotationSource(() => ({
            collectionId,
            source: { id: 's1', name: 'predictions' },
            onDeleted: mocks.onDeleted
        }));

        remove();
        collectionId = 'col-2';
        await mocks.onSuccess?.();

        expect(get(lastAnnotationSource)).toEqual({ 'col-2': 'predictions' });
        expect(mocks.invalidate).toHaveBeenCalledWith('col-1');
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
