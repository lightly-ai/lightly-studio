import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnnotationClasses } from './useAnnotationClasses.svelte';

const mocks = vi.hoisted(() => ({
    mutateAsync: vi.fn(),
    invalidateQueries: vi.fn(),
    createQuery: vi.fn(),
    renameLastAnnotationLabel: vi.fn(),
    removeLastAnnotationLabel: vi.fn(),
    renameRecentClass: vi.fn(),
    removeRecentClass: vi.fn(),
    fetchQuery: vi.fn()
}));

type MutationOptions = { onSettled?: () => unknown };

vi.mock('@tanstack/svelte-query', () => ({
    queryOptions: (options: unknown) => options,
    mutationOptions: (options: unknown) => options,
    // Run onSettled after the call, like the real mutation does.
    createMutation: (getOptions: () => MutationOptions) => ({
        mutateAsync: async (variables: unknown) => {
            try {
                return await mocks.mutateAsync(variables);
            } finally {
                await getOptions().onSettled?.();
            }
        }
    }),
    createQuery: (getOptions: () => unknown) => {
        mocks.createQuery(getOptions());
        return {};
    },
    useQueryClient: () => ({
        invalidateQueries: mocks.invalidateQueries,
        fetchQuery: mocks.fetchQuery
    })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        renameLastAnnotationLabel: mocks.renameLastAnnotationLabel,
        removeLastAnnotationLabel: mocks.removeLastAnnotationLabel
    })
}));
vi.mock('$lib/hooks/useRecentClasses/useRecentClasses', () => ({
    useRecentClasses: () => ({
        renameRecentClass: mocks.renameRecentClass,
        removeRecentClass: mocks.removeRecentClass
    })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

let cleanup = () => {};

const setup = (collectionId = 'collection-1') => {
    let classes!: ReturnType<typeof useAnnotationClasses>;
    cleanup = $effect.root(() => {
        classes = useAnnotationClasses(() => ({ collectionId, datasetId: 'dataset-1' }));
    });
    flushSync();
    return classes;
};

describe('useAnnotationClasses', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.mutateAsync.mockResolvedValue({});
        mocks.fetchQuery.mockResolvedValue([{ collection_id: 'collection-1' }]);
    });

    afterEach(() => cleanup());

    it('renameClass rejects when the rename fails', async () => {
        mocks.mutateAsync.mockRejectedValue(new Error('boom'));
        const classes = setup();

        await expect(classes.renameClass('label-1', 'cat', 'kitty')).rejects.toThrow('boom');
    });

    it('query is disabled without a collection', () => {
        setup('');

        expect(mocks.createQuery).toHaveBeenCalledWith(expect.objectContaining({ enabled: false }));
    });

    it('addClass refreshes all queries', async () => {
        const classes = setup();

        await classes.addClass('wolf');

        expect(mocks.invalidateQueries).toHaveBeenCalledWith();
    });

    it('renameClass refreshes all queries', async () => {
        const classes = setup();

        await classes.renameClass('label-1', 'cat', 'kitty');

        expect(mocks.invalidateQueries).toHaveBeenCalledWith();
    });

    it('deleteClass refreshes all queries', async () => {
        const classes = setup();

        await classes.deleteClass('label-1', 'cat');

        expect(mocks.invalidateQueries).toHaveBeenCalledWith();
    });

    it('renameClass renames the sticky class and the recent classes', async () => {
        const classes = setup();

        await classes.renameClass('label-1', 'cat', 'kitty');

        expect(mocks.renameLastAnnotationLabel).toHaveBeenCalledWith(
            'collection-1',
            'cat',
            'kitty'
        );
        expect(mocks.renameRecentClass).toHaveBeenCalledWith('collection-1', 'cat', 'kitty');
    });

    it('renames and forgets the class in every collection of the dataset', async () => {
        mocks.fetchQuery.mockResolvedValue([
            { collection_id: 'dataset-1' },
            { collection_id: 'collection-1' }
        ]);
        const classes = setup();

        await classes.renameClass('label-1', 'cat', 'kitty');
        await classes.deleteClass('label-2', 'dog');

        for (const collectionId of ['collection-1', 'dataset-1']) {
            expect(mocks.renameLastAnnotationLabel).toHaveBeenCalledWith(
                collectionId,
                'cat',
                'kitty'
            );
            expect(mocks.renameRecentClass).toHaveBeenCalledWith(collectionId, 'cat', 'kitty');
            expect(mocks.removeLastAnnotationLabel).toHaveBeenCalledWith(collectionId, 'dog');
            expect(mocks.removeRecentClass).toHaveBeenCalledWith(collectionId, 'dog');
        }
    });

    it('renames the class in the current collection when the hierarchy does not load', async () => {
        mocks.fetchQuery.mockRejectedValue(new Error('offline'));
        const classes = setup();

        await classes.renameClass('label-1', 'cat', 'kitty');

        expect(mocks.renameRecentClass).toHaveBeenCalledExactlyOnceWith(
            'collection-1',
            'cat',
            'kitty'
        );
    });

    it('renameClass keeps the sticky class when the rename fails', async () => {
        mocks.mutateAsync.mockRejectedValue(new Error('boom'));
        const classes = setup();

        await expect(classes.renameClass('label-1', 'cat', 'kitty')).rejects.toThrow('boom');

        expect(mocks.renameLastAnnotationLabel).not.toHaveBeenCalled();
        expect(mocks.renameRecentClass).not.toHaveBeenCalled();
    });

    it('deleteClass forgets the class as sticky and recent class', async () => {
        const classes = setup();

        await classes.deleteClass('label-1', 'cat');

        expect(mocks.removeLastAnnotationLabel).toHaveBeenCalledWith('collection-1', 'cat');
        expect(mocks.removeRecentClass).toHaveBeenCalledWith('collection-1', 'cat');
    });

    it('deleteClass keeps the sticky class when the delete fails', async () => {
        mocks.mutateAsync.mockRejectedValue(new Error('boom'));
        const classes = setup();

        await expect(classes.deleteClass('label-1', 'cat')).rejects.toThrow('boom');

        expect(mocks.removeLastAnnotationLabel).not.toHaveBeenCalled();
        expect(mocks.removeRecentClass).not.toHaveBeenCalled();
    });
});
