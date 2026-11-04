import { flushSync } from 'svelte';
import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCustomColorStore } from '$lib/hooks/createCustomColorStore';
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
// A real color store, so the tests check where colors end up.
let colors: ReturnType<typeof createCustomColorStore>;
vi.mock('$lib/hooks/useCustomLabelColors', () => ({
    useCustomLabelColors: () => colors
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
        colors = createCustomColorStore();
        mocks.mutateAsync.mockResolvedValue({});
    });

    afterEach(() => cleanup());

    it('renameClass moves the custom color to the new name', async () => {
        colors.setCustomColor('cat', '#ff0000', 0.5);
        const classes = setup();

        await classes.renameClass('label-1', 'cat', 'kitty');

        expect(colors.getCustomColor('kitty')).toEqual({ color: '#ff0000', alpha: 0.5 });
        expect(colors.getCustomColor('cat')).toBeUndefined();
    });

    it('renameClass keeps the custom color when the name is unchanged', async () => {
        colors.setCustomColor('cat', '#ff0000', 0.5);
        const classes = setup();

        await classes.renameClass('label-1', 'cat', 'cat');

        expect(colors.getCustomColor('cat')).toEqual({ color: '#ff0000', alpha: 0.5 });
    });

    it('renameClass keeps colors when the rename fails', async () => {
        colors.setCustomColor('cat', '#ff0000', 0.5);
        mocks.mutateAsync.mockRejectedValue(new Error('boom'));
        const classes = setup();

        await expect(classes.renameClass('label-1', 'cat', 'kitty')).rejects.toThrow('boom');

        expect(colors.getCustomColor('cat')).toEqual({ color: '#ff0000', alpha: 0.5 });
        expect(colors.getCustomColor('kitty')).toBeUndefined();
    });

    it('renameClass does not save an open picker preview', async () => {
        const owner = Symbol();
        colors.setCustomColor('cat', '#112233', 1);
        colors.setPreviewColor('cat', { color: '#abcdef', alpha: 1 }, owner);
        const classes = setup();

        await classes.renameClass('label-1', 'cat', 'kitty');
        colors.clearPreviewColor('cat', owner);

        expect(colors.getCustomColor('kitty')?.color).toBe('#112233');
        expect(JSON.stringify(get(colors.customColorsStore))).not.toContain('#abcdef');
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

        await classes.deleteClass('label-1');

        expect(mocks.invalidateQueries).toHaveBeenCalledWith();
    });
});
