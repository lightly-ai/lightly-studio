import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnnotationClasses } from './useAnnotationClasses.svelte';

const mocks = vi.hoisted(() => ({
    mutateAsync: vi.fn(),
    invalidateQueries: vi.fn(),
    createQuery: vi.fn()
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
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
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
    });

    afterEach(() => cleanup());

    it('renameClass rejects when the rename fails', async () => {
        mocks.mutateAsync.mockRejectedValue(new Error('boom'));
        const classes = setup();

        await expect(classes.renameClass('label-1', 'kitty')).rejects.toThrow('boom');
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

        await classes.renameClass('label-1', 'kitty');

        expect(mocks.invalidateQueries).toHaveBeenCalledWith();
    });

    it('deleteClass refreshes all queries', async () => {
        const classes = setup();

        await classes.deleteClass('label-1');

        expect(mocks.invalidateQueries).toHaveBeenCalledWith();
    });
});
