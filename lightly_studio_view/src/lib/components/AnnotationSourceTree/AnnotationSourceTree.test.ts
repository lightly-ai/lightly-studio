import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnnotationPairFilter } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';
import { NO_MATCH_PAIR } from '$lib/hooks/useAnnotationPairFilter/pairFilter.helpers';
import AnnotationSourceTree from './AnnotationSourceTree.svelte';
import { useTreeGroupBy } from './useTreeGroupBy';

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
    countMode: 'samples' as const
};
const unannotatedCount = { current_count: 5, total_count: 7 };
const filter = () => useAnnotationPairFilter(COLLECTION);
const tickedPairs = () => get(filter().pairs);

describe('AnnotationSourceTree', () => {
    beforeEach(() => {
        filter().clear();
        filter().setKnownPairs([]);
        useTreeGroupBy(COLLECTION).setGroupBy('source');
        mocks.sources = [
            { collection_id: 'gt', name: 'ground_truth' },
            { collection_id: 'model', name: 'model_v1.2' }
        ];
        mocks.counts = [
            count('gt', 'deer', 3, 4),
            count('gt', 'raccoon', 1, 2),
            count('model', 'deer', 2, 2)
        ];
    });

    it('starts with everything ticked and sends no pair filter', () => {
        render(AnnotationSourceTree, { ...defaultProps, unannotatedCount });

        const tree = screen.getByTestId('annotation-source-tree');
        for (const box of within(tree).getAllByRole('checkbox')) {
            expect(box).toHaveAttribute('aria-checked', 'true');
        }
        expect(screen.getByText('Showing everything')).toBeInTheDocument();
        expect(tickedPairs()).toEqual([]);
        expect(get(filter().includeUnannotated)).toBe(false);
        expect(screen.queryByRole('button', { name: /annotation source ground_truth/ })).toBeNull();
    });

    it('sends the ticked pairs once one is unticked, and offers show all and hide all', async () => {
        render(AnnotationSourceTree, { ...defaultProps, unannotatedCount });

        await userEvent.click(screen.getByRole('checkbox', { name: 'raccoon in ground_truth' }));

        expect(screen.getByRole('checkbox', { name: 'ground_truth' })).toHaveAttribute(
            'aria-checked',
            'mixed'
        );
        expect(tickedPairs()).toEqual([
            { collection_id: 'gt', annotation_label_id: 'deer-id' },
            { collection_id: 'model', annotation_label_id: 'deer-id' }
        ]);
        expect(get(filter().includeUnannotated)).toBe(true);
        expect(screen.getByText('1 hidden')).toBeInTheDocument();

        await userEvent.click(screen.getByRole('button', { name: 'Show all' }));
        expect(tickedPairs()).toEqual([]);
    });

    it('groups by class with sources as children', async () => {
        render(AnnotationSourceTree, defaultProps);

        await userEvent.click(screen.getByRole('button', { name: 'By class' }));

        const rows = screen.getAllByTestId('annotation-source-row');
        expect(
            rows.map((row) => within(row).getByRole('checkbox').getAttribute('aria-label'))
        ).toEqual(['deer', 'raccoon']);
        expect(within(rows[0]).getByText('2 sources')).toBeInTheDocument();

        await userEvent.click(within(rows[0]).getByRole('checkbox', { name: 'deer' }));
        // The group checkbox ticks the group; there is no separate "All" action.
        expect(screen.queryByRole('button', { name: /^Show all of/ })).toBeNull();
        expect(tickedPairs()).toEqual([{ collection_id: 'gt', annotation_label_id: 'raccoon-id' }]);
    });

    it('filters on source or class names and acts on the matches', async () => {
        render(AnnotationSourceTree, { ...defaultProps, unannotatedCount });
        const search = screen.getByRole('textbox', { name: 'Search sources and classes' });

        await userEvent.type(search, 'RAC');
        expect(screen.getAllByTestId('annotation-source-node')).toHaveLength(1);
        expect(screen.getByTestId('annotation-class-name').querySelector('mark')).toHaveTextContent(
            'rac'
        );
        expect(screen.queryByText('No annotations')).toBeNull();
        expect(screen.getByText('1 match')).toBeInTheDocument();

        await userEvent.click(screen.getByRole('button', { name: 'Show only' }));
        expect(tickedPairs()).toEqual([{ collection_id: 'gt', annotation_label_id: 'raccoon-id' }]);
        expect(get(filter().includeUnannotated)).toBe(false);

        await userEvent.clear(search);
        await userEvent.type(search, 'model');
        expect(screen.getAllByTestId('annotation-source-node')).toHaveLength(1);
        expect(screen.getByRole('checkbox', { name: 'deer in model_v1.2' })).toBeInTheDocument();
    });

    it('toggles the regex search and reports an invalid pattern', async () => {
        render(AnnotationSourceTree, defaultProps);
        const toggle = screen.getByRole('button', { name: 'Use regular expression' });
        const search = screen.getByRole('textbox', { name: 'Search sources and classes' });
        expect(toggle).toHaveAttribute('aria-pressed', 'false');

        await userEvent.type(search, 'v1.2');
        expect(screen.getAllByTestId('annotation-source-node')).toHaveLength(1);

        await userEvent.click(toggle);
        expect(toggle).toHaveAttribute('aria-pressed', 'true');
        await userEvent.clear(search);
        await userEvent.type(search, '(');
        expect(screen.getByText('Invalid pattern')).toBeInTheDocument();
        expect(search).toHaveAttribute('aria-invalid', 'true');
        expect(screen.getAllByTestId('annotation-source-node')).toHaveLength(2);
    });

    it('collapses groups when there are more than 3, with a summary when partly ticked', () => {
        filter().togglePair({
            collection_id: 'gt',
            annotation_label_id: 'deer-id',
            label_name: 'deer'
        });
        mocks.sources = [
            ...mocks.sources,
            { collection_id: 'a', name: 'a_source' },
            { collection_id: 'b', name: 'b_source' }
        ];

        render(AnnotationSourceTree, defaultProps);

        expect(screen.queryByRole('checkbox', { name: 'deer in ground_truth' })).toBeNull();
        const summaries = screen.getAllByTestId('annotation-group-summary');
        expect(summaries).toHaveLength(1);
        expect(summaries[0]).toHaveTextContent('1/2');
    });

    it('collapses and expands every group at once, and stays open while searching', async () => {
        render(AnnotationSourceTree, defaultProps);
        const childRows = () => screen.queryAllByTestId('annotation-class-item');
        expect(childRows()).toHaveLength(3);

        await userEvent.click(screen.getByRole('button', { name: 'Collapse all' }));
        expect(childRows()).toHaveLength(0);

        const search = screen.getByRole('textbox', { name: 'Search sources and classes' });
        await userEvent.type(search, 'deer');
        expect(childRows()).toHaveLength(2);
        await userEvent.clear(search);
        expect(childRows()).toHaveLength(0);

        await userEvent.click(screen.getByRole('button', { name: 'Expand all' }));
        expect(childRows()).toHaveLength(3);
    });

    it('shows one source of the annotations grid as a flat class list searched by class', async () => {
        render(AnnotationSourceTree, { ...defaultProps, singleSourceId: 'gt' });

        expect(screen.queryByRole('button', { name: 'By class' })).toBeNull();
        expect(screen.queryByRole('button', { name: 'Collapse all' })).toBeNull();
        expect(screen.queryByTestId('annotation-source-row')).toBeNull();

        await userEvent.click(screen.getByRole('button', { name: 'Use regular expression' }));
        await userEvent.type(screen.getByRole('textbox', { name: 'Search classes' }), '^$');
        expect(screen.getByText('No matches')).toBeInTheDocument();
    });

    it('shows a flat class list with no source row for one source', () => {
        mocks.sources = [{ collection_id: 'gt', name: 'ground_truth' }];

        render(AnnotationSourceTree, defaultProps);

        expect(screen.queryByTestId('annotation-source-row')).not.toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: 'deer in ground_truth' })).toBeInTheDocument();
    });

    it('pins "No annotations", unticks it and shows only it', async () => {
        render(AnnotationSourceTree, { ...defaultProps, unannotatedCount });

        const row = screen.getByRole('checkbox', { name: 'No annotations' });
        expect(screen.getByText('5 / 7')).toBeInTheDocument();

        await userEvent.click(row);
        expect(get(filter().unannotatedTicked)).toBe(false);
        expect(tickedPairs()).toHaveLength(3);

        await userEvent.click(screen.getByRole('button', { name: 'Show only No annotations' }));
        expect(get(filter().unannotatedTicked)).toBe(true);
        expect(get(filter().includeUnannotated)).toBe(true);
        expect(tickedPairs()).toEqual([NO_MATCH_PAIR]);
    });
});
