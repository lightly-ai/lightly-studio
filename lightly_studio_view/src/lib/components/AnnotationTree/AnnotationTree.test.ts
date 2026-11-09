import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationPairCount } from '$lib/api/lightly_studio_local';
import AnnotationTreeTestWrapper from './AnnotationTreeTestWrapper.test.svelte';

const mocks = vi.hoisted(() => ({
    sources: [] as { collection_id: string; name: string }[],
    pairs: [] as AnnotationPairCount[]
}));

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    readAnnotationCollections: vi.fn(async () => ({ data: mocks.sources })),
    countImageAnnotationsByPair: vi.fn(async () => ({ data: mocks.pairs })),
    countUnannotatedImagesBySource: vi.fn(async () => ({
        data: mocks.sources.map((source) => ({
            annotation_collection_id: source.collection_id,
            current_count: 3,
            total_count: 3
        }))
    }))
}));

const pair = (sourceId: string, labelId: string, name: string): AnnotationPairCount => ({
    annotation_collection_id: sourceId,
    annotation_label_id: labelId,
    label_name: name,
    current_count: 5,
    total_count: 5
});

let testCount = 0;

const renderTree = () => {
    testCount += 1;
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // The tree state lives in session storage per collection, so each test gets its own.
    render(AnnotationTreeTestWrapper, { client, collectionId: `images-${testCount}` });
};

const groupNamed = async (name: string) => {
    const groups = await screen.findAllByTestId('annotation-tree-group');
    const group = groups.find(
        (element) => within(element).getByTestId('annotation-tree-group-name').textContent === name
    );
    if (!group) throw new Error(`No group named ${name}`);
    return group;
};

const childNames = (group: HTMLElement) =>
    within(group)
        .queryAllByTestId('annotation-tree-row-name')
        .map((element) => element.textContent);

describe('AnnotationTree', () => {
    beforeEach(() => {
        mocks.sources = [
            { collection_id: 'src-labels', name: 'labels' },
            { collection_id: 'src-model', name: 'model_v1' }
        ];
        mocks.pairs = [
            pair('src-labels', 'lbl-car', 'car'),
            pair('src-labels', 'lbl-person', 'person'),
            pair('src-model', 'lbl-car', 'car')
        ];
    });

    it('renders a source with "No annotations" first and its classes indented under it', async () => {
        renderTree();

        const labels = await groupNamed('labels');
        await waitFor(() =>
            expect(childNames(labels)).toEqual(['No annotations', 'car', 'person'])
        );
        expect(within(labels).getByTestId('annotation-tree-children')).toBeInTheDocument();
    });

    it('shows a dash on the group checkbox when some children are unticked', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('checkbox', { name: 'car in labels' }));

        await waitFor(() =>
            expect(screen.getByRole('checkbox', { name: 'labels' })).toHaveAttribute(
                'aria-checked',
                'mixed'
            )
        );
    });

    it('keeps the source "No annotations" ticked on "Only" for a source', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('button', { name: 'Only labels' }));

        await waitFor(() =>
            expect(screen.getByRole('checkbox', { name: 'model_v1' })).toHaveAttribute(
                'aria-checked',
                'false'
            )
        );
        expect(screen.getByRole('checkbox', { name: 'labels' })).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    it('unticks every "No annotations" row on "Only" for a class', async () => {
        renderTree();

        await fireEvent.click(await screen.findByRole('button', { name: 'Only car in labels' }));

        await waitFor(() =>
            expect(
                screen.getByRole('checkbox', { name: 'No annotations in labels' })
            ).toHaveAttribute('aria-checked', 'false')
        );
        expect(screen.getByRole('checkbox', { name: 'car in labels' })).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });
});
