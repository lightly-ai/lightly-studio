import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationPairCount } from '$lib/api/lightly_studio_local';
import { useAnnotationTreeState } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
import AnnotationsFlatTreeTestWrapper from './AnnotationsFlatTreeTestWrapper.test.svelte';

const mocks = vi.hoisted(() => ({
    readAnnotations: vi.fn(),
    countPairs: vi.fn()
}));

vi.mock('$lib/hooks/useSettings', async (importOriginal) => {
    const { readable } = await import('svelte/store');
    const original = await importOriginal<typeof import('$lib/hooks/useSettings')>();
    return {
        ...original,
        useSettings: () => ({
            ...original.useSettings(),
            annotationColorModeStore: readable('source')
        })
    };
});

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    readAnnotationCollections: vi.fn(async () => ({
        data: [
            { collection_id: 'src-labels', name: 'labels' },
            { collection_id: 'src-model', name: 'model_v1' }
        ]
    })),
    countImageAnnotationsByPair: mocks.countPairs,
    readAnnotationsWithPayload: mocks.readAnnotations
}));

const pair = (sourceId: string, labelId: string, name: string): AnnotationPairCount => ({
    annotation_collection_id: sourceId,
    annotation_label_id: labelId,
    label_name: name,
    current_count: 5,
    total_count: 5
});

let testCount = 0;

// The Annotations tab keeps its tree state under its annotation source.
const tabTree = useAnnotationTreeState('src-labels');

const renderGridTree = (setUp?: (tree: ReturnType<typeof useAnnotationTreeState>) => void) => {
    testCount += 1;
    setUp?.(tabTree);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(AnnotationsFlatTreeTestWrapper, {
        client,
        collectionId: `images-${testCount}`,
        sourceId: 'src-labels'
    });
};

const lastBody = () => mocks.readAnnotations.mock.lastCall?.[0].body;

describe('AnnotationTree on the Annotations grid', () => {
    beforeEach(() => {
        mocks.countPairs.mockReset();
        mocks.countPairs.mockResolvedValue({
            data: [
                pair('src-labels', 'lbl-car', 'car'),
                pair('src-labels', 'lbl-person', 'person'),
                pair('src-model', 'lbl-car', 'car')
            ]
        });
        tabTree.resetTicks();
        mocks.readAnnotations.mockReset();
        mocks.readAnnotations.mockResolvedValue({
            data: { data: [], total_count: 0, nextCursor: null }
        });
    });

    it('lists only the classes of the tab source, without switches or "No annotations"', async () => {
        renderGridTree();

        await screen.findByRole('checkbox', { name: 'car in labels' });

        expect(screen.getByRole('checkbox', { name: 'person in labels' })).toBeInTheDocument();
        expect(screen.getAllByTestId('annotation-tree-row-name')).toHaveLength(2);
        expect(screen.queryByRole('button', { name: 'By class' })).not.toBeInTheDocument();
        expect(screen.queryByRole('group', { name: 'Color by' })).not.toBeInTheDocument();
        expect(screen.queryByText('No annotations')).not.toBeInTheDocument();
        expect(screen.getByPlaceholderText('Search classes…')).toBeInTheDocument();
    });

    it('shows class dots although the saved Color by mode is Source', async () => {
        renderGridTree();

        await screen.findByRole('checkbox', { name: 'car in labels' });

        expect(screen.getAllByTestId('annotation-tree-class-dot')).toHaveLength(2);
    });

    it('sends no pair filter while everything is ticked', async () => {
        renderGridTree();

        await waitFor(() => expect(mocks.readAnnotations).toHaveBeenCalled());

        expect(lastBody().annotation_pairs).toBeUndefined();
    });

    it('ignores unticked pairs of other sources and of classes that are gone', async () => {
        renderGridTree((tree) =>
            tree.setTicked(
                [
                    { collection_id: 'src-model', annotation_label_id: 'lbl-car' },
                    { collection_id: 'src-labels', annotation_label_id: 'lbl-gone' }
                ],
                false
            )
        );

        await waitFor(() => expect(mocks.readAnnotations).toHaveBeenCalled());

        expect(lastBody().annotation_pairs).toBeUndefined();
    });

    it('sends only the ticked pairs of the tab source after unticking a class', async () => {
        renderGridTree();

        await fireEvent.click(await screen.findByRole('checkbox', { name: 'car in labels' }));

        await waitFor(() =>
            expect(lastBody().annotation_pairs).toEqual([
                { collection_id: 'src-labels', annotation_label_id: 'lbl-person' }
            ])
        );
    });

    it('keeps the ticks of the Images grid when a class is unticked', async () => {
        renderGridTree();

        await fireEvent.click(await screen.findByRole('checkbox', { name: 'car in labels' }));

        await waitFor(() =>
            expect(get(tabTree.untickedPairs)).toEqual([
                { collection_id: 'src-labels', annotation_label_id: 'lbl-car' }
            ])
        );
        expect(get(useAnnotationTreeState(`images-${testCount}`).untickedPairs)).toEqual([]);
    });

    it('sends an empty pair list when every class is unticked', async () => {
        renderGridTree();

        await fireEvent.click(await screen.findByRole('checkbox', { name: 'All annotations' }));

        await waitFor(() => expect(lastBody().annotation_pairs).toEqual([]));
    });

    it('holds the request back while the pair counts load with a class unticked', async () => {
        mocks.countPairs.mockReturnValue(new Promise(() => {}));

        renderGridTree((tree) =>
            tree.setTicked([{ collection_id: 'src-labels', annotation_label_id: 'lbl-car' }], false)
        );

        await new Promise((resolve) => setTimeout(resolve, 20));
        expect(mocks.readAnnotations).not.toHaveBeenCalled();
    });
});
