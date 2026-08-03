import type { ImageView } from '$lib/api/lightly_studio_local';
import { useQueryClient } from '@tanstack/svelte-query';
import type { TagView } from '$lib/services/types';
import { flushSync } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { GRID_IMAGE_SEARCH_DROP_EVENT } from '$lib/components/GridItem';
import { useImagesContextMenu } from './useImagesContextMenu.svelte';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, useQueryClient: vi.fn() };
});

const tagMutations = vi.hoisted(() => ({
    assignTag: vi.fn(),
    assignByName: vi.fn(),
    removeTag: vi.fn()
}));

vi.mock('$lib/hooks', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/hooks')>();
    return {
        ...actual,
        useTagMutations: () => ({
            busy: { subscribe: (run: (v: boolean) => void) => (run(false), () => {}) },
            ...tagMutations
        })
    };
});

function makeTag(tag_id: string, name: string): TagView {
    return {
        tag_id,
        name,
        kind: 'sample',
        created_at: new Date('2024-01-01'),
        updated_at: new Date('2024-01-01')
    };
}

const trainTag = makeTag('tag-train', 'train');
const blurryTag = makeTag('tag-blurry', 'blurry');

function makeSample(sample_id: string, tags: TagView[] = []): ImageView {
    return { sample_id, file_name: `${sample_id}.png`, tags } as unknown as ImageView;
}

interface SetupOverrides {
    samples?: ImageView[];
    selectedSampleIds?: Set<string>;
    tags?: TagView[];
}

/** Runs the hook inside a reactive root so `$derived` values settle. */
function setup({
    samples = [makeSample('s1', [trainTag]), makeSample('s2'), makeSample('s3')],
    selectedSampleIds = new Set<string>(),
    tags = [trainTag, blurryTag]
}: SetupOverrides = {}) {
    const onOpenSample = vi.fn();
    const setQueriesData = vi.fn();
    vi.mocked(useQueryClient).mockReturnValue({
        setQueriesData
    } as unknown as ReturnType<typeof useQueryClient>);

    let menu!: ReturnType<typeof useImagesContextMenu>;
    const cleanup = $effect.root(() => {
        menu = useImagesContextMenu({
            collectionId: 'collection-1',
            getSamples: () => samples,
            getSelectedSampleIds: () => selectedSampleIds,
            getAllTags: () => tags,
            getSelectAllSnapshot: () => null,
            getSamplesQueryKey: () => ['readImagesInfinite'],
            onSamplesRefetch: vi.fn(),
            onTagsRefetch: vi.fn(),
            onOpenSample
        });
    });

    return { menu, onOpenSample, setQueriesData, cleanup };
}

/** Builds a right-click event whose target resolves to the tile at `index`. */
function contextMenuEventAt(index: number | null): MouseEvent {
    const tile = document.createElement('div');
    tile.setAttribute('data-testid', 'sample-grid-item');
    if (index !== null) tile.dataset.index = String(index);
    const event = new MouseEvent('contextmenu', { bubbles: true });
    Object.defineProperty(event, 'target', { value: index === null ? document.body : tile });
    return event;
}

describe('useImagesContextMenu', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('targets the clicked sample and labels the menu with its file name', () => {
        const { menu, cleanup } = setup();

        expect(menu.resolveTarget(contextMenuEventAt(0))).toBe(true);
        flushSync();

        expect(menu.headerLabel).toBe('s1.png');
        expect(menu.isSelectionTarget).toBe(false);
        expect(menu.tagStates).toEqual({ 'tag-train': 'checked', 'tag-blurry': 'unchecked' });
        cleanup();
    });

    it('targets the whole selection and reports mixed tag state', () => {
        const { menu, cleanup } = setup({ selectedSampleIds: new Set(['s1', 's2']) });

        menu.resolveTarget(contextMenuEventAt(0));
        flushSync();

        expect(menu.headerLabel).toBe('2 samples');
        expect(menu.isSelectionTarget).toBe(true);
        // s1 has train, s2 does not.
        expect(menu.tagStates['tag-train']).toBe('indeterminate');
        cleanup();
    });

    it('keeps the selection out of the target when clicking outside it', () => {
        const { menu, cleanup } = setup({ selectedSampleIds: new Set(['s1', 's2']) });

        menu.resolveTarget(contextMenuEventAt(2));
        flushSync();

        expect(menu.headerLabel).toBe('s3.png');
        expect(menu.isSelectionTarget).toBe(false);
        cleanup();
    });

    it('reports no target when the right-click missed a tile', () => {
        const { menu, cleanup } = setup();

        expect(menu.resolveTarget(contextMenuEventAt(null))).toBe(false);
        cleanup();
    });

    it('assigns an unchecked tag and patches the cache optimistically', () => {
        const { menu, setQueriesData, cleanup } = setup();

        menu.resolveTarget(contextMenuEventAt(1));
        flushSync();
        menu.toggleTag('tag-train');

        expect(tagMutations.assignTag).toHaveBeenCalledWith('tag-train');
        expect(tagMutations.removeTag).not.toHaveBeenCalled();
        expect(setQueriesData).toHaveBeenCalledTimes(1);
        cleanup();
    });

    it('removes a checked tag', () => {
        const { menu, cleanup } = setup();

        menu.resolveTarget(contextMenuEventAt(0));
        flushSync();
        menu.toggleTag('tag-train');

        expect(tagMutations.removeTag).toHaveBeenCalledWith('tag-train');
        expect(tagMutations.assignTag).not.toHaveBeenCalled();
        cleanup();
    });

    it('notes when only some targets have loaded tag data', () => {
        const { menu, cleanup } = setup({
            samples: [makeSample('s1', [trainTag])],
            selectedSampleIds: new Set(['s1', 'not-loaded'])
        });

        menu.resolveTarget(contextMenuEventAt(0));
        flushSync();

        expect(menu.knownTargetNote).toBe('Tag state shown for 1 of 2 loaded samples');
        cleanup();
    });

    it('opens the clicked sample and dispatches a similarity search for it', () => {
        const { menu, onOpenSample, cleanup } = setup();
        const onDrop = vi.fn();
        window.addEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, onDrop);

        menu.resolveTarget(contextMenuEventAt(2));
        flushSync();
        menu.openTarget();
        menu.findSimilarTarget();

        expect(onOpenSample).toHaveBeenCalledWith('s3');
        expect(onDrop).toHaveBeenCalledTimes(1);
        expect((onDrop.mock.calls[0][0] as CustomEvent).detail.fileName).toBe('s3.png');

        window.removeEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, onDrop);
        cleanup();
    });
});
