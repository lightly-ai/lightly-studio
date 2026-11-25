import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { EvaluationSliceMetricsView } from '$lib/api/lightly_studio_local';
import { makeComparedRun, makeMetricsView } from '../fixtures';
import TagSection from './TagSection.svelte';

const tags = [
    { tag_id: 't1', name: 'night' },
    { tag_id: 't2', name: 'rain' }
];

const slice = (map: number, count: number): EvaluationSliceMetricsView => ({
    tag_id: 't1',
    tag_name: 'night',
    evaluated_sample_count: count,
    metrics: { ...makeMetricsView('x').metrics, mean_average_precision: map }
});

const withSlice = (id: string, map: number, count: number) => {
    const run = makeComparedRun(id);
    run.metrics.slices = [slice(map, count)];
    return run;
};

const defaultProps = {
    taskType: 'object_detection' as const,
    runs: [withSlice('run-a', 0.3, 4), withSlice('run-b', 0.7, 4)],
    tags,
    selectedTagIds: ['t1'],
    onSelectedTagIdsChange: vi.fn()
};

describe('TagSection', () => {
    it('shows the full set and each selected tag, with the best run in bold', () => {
        render(TagSection, { props: defaultProps });

        expect(screen.getByRole('tab', { name: 'mAP' })).toHaveAttribute('aria-selected', 'true');
        const table = screen.getByRole('table');
        const nightRow = within(table).getByRole('row', { name: /night/ });
        expect(nightRow).toHaveTextContent('4 images');
        expect(within(nightRow).getByText('0.700')).toHaveAttribute('data-best', 'true');
        expect(within(table).getByRole('row', { name: /Full set/ })).toBeInTheDocument();
    });

    it('asks for tags when none is selected', () => {
        render(TagSection, { props: { ...defaultProps, selectedTagIds: [] } });

        expect(
            screen.getByText('Select tags to compare the runs on subsets of the images.')
        ).toBeInTheDocument();
        expect(screen.queryByRole('table')).not.toBeInTheDocument();
    });

    it('reports a changed tag selection', async () => {
        const onSelectedTagIdsChange = vi.fn();
        render(TagSection, { props: { ...defaultProps, onSelectedTagIdsChange } });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'rain' }));

        expect(onSelectedTagIdsChange).toHaveBeenCalledWith(['t1', 't2']);
    });

    it('marks a tag where the runs evaluated different images', () => {
        render(TagSection, {
            props: {
                ...defaultProps,
                runs: [withSlice('run-a', 0.3, 4), withSlice('run-b', 0.7, 2)]
            }
        });

        const nightRow = within(screen.getByRole('table')).getByRole('row', { name: /night/ });
        expect(nightRow).toHaveTextContent('different images');
    });
});
