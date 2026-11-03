import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { useAnnotationPairFilter } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';
import AnnotationSourceTree from './AnnotationSourceTree.svelte';

const mocks = vi.hoisted(() => ({
    sources: [] as { collection_id: string; name: string }[],
    counts: [] as {
        annotation_collection_id: string;
        annotation_label_id: string;
        label_name: string;
        current_count: number;
        total_count: number;
    }[]
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({
        get data() {
            return mocks.sources;
        }
    })
}));

vi.mock('./useSourceLabelCounts.svelte', () => ({
    useSourceLabelCounts: () => ({
        get data() {
            return mocks.counts;
        }
    })
}));

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    return { useSettings: () => ({ enforceColoringByClassStore: writable(true) }) };
});

vi.mock('$lib/hooks/useCustomLabelColors', async () => {
    const { writable } = await import('svelte/store');
    return {
        useCustomLabelColors: () => ({
            customLabelColorsStore: writable({}),
            getCustomColor: () => undefined,
            hasCustomColor: () => false
        })
    };
});

const COLLECTION = 'images-1';
const count = (source: string, label: string, current: number, total: number) => ({
    annotation_collection_id: source,
    annotation_label_id: `${label}-id`,
    label_name: label,
    current_count: current,
    total_count: total
});
const defaultProps = {
    collectionId: COLLECTION,
    countsCollectionId: COLLECTION,
    countMode: 'samples' as const,
    showVisibilityToggle: true
};

describe('AnnotationSourceTree', () => {
    beforeEach(() => {
        useAnnotationPairFilter(COLLECTION).clear();
        sessionStorage.clear();
        mocks.sources = [
            { collection_id: 'gt', name: 'ground_truth' },
            { collection_id: 'model', name: 'model_v1' }
        ];
        mocks.counts = [
            count('gt', 'deer', 3, 4),
            count('gt', 'raccoon', 1, 2),
            count('model', 'deer', 2, 2)
        ];
        useAnnotationCollectionsFilter().setCollectionIdToName({
            gt: 'ground_truth',
            model: 'model_v1'
        });
        useAnnotationCollectionsFilter().setSelectedCollectionIds(['gt', 'model']);
    });

    it('nests the classes under a tri-state source row with chevron, count and eye', async () => {
        render(AnnotationSourceTree, defaultProps);

        const rows = screen.getAllByTestId('annotation-source-row');
        expect(rows).toHaveLength(2);
        const groundTruth = rows[0];
        expect(within(groundTruth).getByRole('button', { name: 'Collapse ground_truth' }));
        expect(within(groundTruth).getByText('4 / 6')).toBeInTheDocument();
        expect(
            within(groundTruth).getByRole('button', { name: 'Hide annotation source ground_truth' })
        ).toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: 'deer in ground_truth' })).toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: 'deer in model_v1' })).toBeInTheDocument();

        const sourceBox = within(groundTruth).getByRole('checkbox', { name: 'ground_truth' });
        expect(sourceBox).toHaveAttribute('aria-checked', 'false');
        await userEvent.click(screen.getByRole('checkbox', { name: 'deer in ground_truth' }));
        expect(sourceBox).toHaveAttribute('aria-checked', 'mixed');
        expect(get(useAnnotationPairFilter(COLLECTION).pairs)).toEqual([
            { collection_id: 'gt', annotation_label_id: 'deer-id' }
        ]);

        await userEvent.click(sourceBox);
        expect(sourceBox).toHaveAttribute('aria-checked', 'true');
        expect(get(useAnnotationPairFilter(COLLECTION).pairs)).toHaveLength(2);
    });

    it('shows a flat class list with no source row for one source', () => {
        mocks.sources = [{ collection_id: 'gt', name: 'ground_truth' }];

        render(AnnotationSourceTree, defaultProps);

        expect(screen.queryByTestId('annotation-source-row')).not.toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: 'deer in ground_truth' })).toBeInTheDocument();
        expect(
            screen.getByRole('checkbox', { name: 'raccoon in ground_truth' })
        ).toBeInTheDocument();
    });

    it('marks a source row with a tooltip only when there are several sources', () => {
        const { unmount } = render(AnnotationSourceTree, { props: defaultProps });
        expect(screen.getAllByTitle('Annotation source').length).toBeGreaterThan(1);
        unmount();
        mocks.sources = [{ collection_id: 'gt', name: 'ground_truth' }];
        render(AnnotationSourceTree, { props: defaultProps });
        expect(screen.queryByTitle('Annotation source')).not.toBeInTheDocument();
    });

    it('filters classes across sources while searching and keeps the pinned row', async () => {
        render(AnnotationSourceTree, {
            ...defaultProps,
            unannotatedRow: { current_count: 5, total_count: 7, selected: false, onToggle: vi.fn() }
        });
        const search = screen.getByRole('textbox', { name: 'Search annotation classes' });

        await userEvent.type(search, 'RAC');
        expect(screen.getAllByTestId('annotation-source-node')).toHaveLength(1);
        expect(
            screen.getByRole('checkbox', { name: 'raccoon in ground_truth' })
        ).toBeInTheDocument();
        expect(screen.queryByRole('checkbox', { name: 'deer in ground_truth' })).toBeNull();
        expect(screen.getByText('No annotations')).toBeInTheDocument();

        await userEvent.clear(search);
        await userEvent.type(search, 'zebra');
        expect(screen.getByText('No matching annotation classes')).toBeInTheDocument();
        expect(screen.getByText('No annotations')).toBeInTheDocument();
    });

    it('renders an empty source collapsed, with no children', () => {
        mocks.sources = [...mocks.sources, { collection_id: 'empty', name: 'empty_source' }];

        render(AnnotationSourceTree, defaultProps);

        const rows = screen.getAllByTestId('annotation-source-row');
        const chevron = within(rows[2]).getByRole('button', { name: 'Expand empty_source' });
        expect(chevron).toBeDisabled();
        expect(chevron).toHaveAttribute('aria-expanded', 'false');
        const nodes = screen.getAllByTestId('annotation-source-node');
        expect(within(nodes[2]).queryAllByTestId('annotation-class-item')).toHaveLength(0);
    });

    it('hides a class under every source from one class eye', async () => {
        render(AnnotationSourceTree, defaultProps);

        const nodes = screen.getAllByTestId('annotation-source-node');
        await userEvent.click(
            within(nodes[0]).getByRole('button', { name: 'Hide annotation class deer' })
        );

        expect(
            within(nodes[1]).getByRole('button', { name: 'Show annotation class deer' })
        ).toBeInTheDocument();
    });

    it('pins "No annotations" at the bottom and toggles it', async () => {
        const onToggle = vi.fn();

        render(AnnotationSourceTree, {
            ...defaultProps,
            unannotatedRow: { current_count: 5, total_count: 7, selected: false, onToggle }
        });

        const tree = screen.getByTestId('annotation-source-tree');
        const checkboxes = within(tree).getAllByRole('checkbox');
        const last = checkboxes[checkboxes.length - 1];
        expect(last).toHaveAccessibleName('No annotations');
        expect(within(tree).getByText('5 / 7')).toBeInTheDocument();

        await userEvent.click(last);
        expect(onToggle).toHaveBeenCalledOnce();
    });
});
