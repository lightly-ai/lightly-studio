import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import type { ImageSortExpr } from '$lib/hooks/useImagesInfinite/types';
import type { ImageView } from '$lib/api/lightly_studio_local';
import SampleImageGridItem from './SampleImageGridItem.svelte';

const imageSortBy = writable<ImageSortExpr[] | null>(null);
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({ imageSortBy })
}));

vi.mock('..', async () => {
    const [{ default: SampleAnnotations }, { default: SampleImage }] = await Promise.all([
        import('./SampleAnnotations.mock.svelte'),
        import('./Empty.mock.svelte')
    ]);
    return { SampleAnnotations, SampleImage };
});

vi.mock('$lib/components/SampleClassificationPills/SampleClassificationPills.svelte', async () => {
    const module = await import('./Empty.mock.svelte');
    return { default: module.default };
});

describe('SampleImageGridItem', () => {
    beforeEach(() => imageSortBy.set(null));

    it('marks missing evaluation results and leaves ordinary missing sort values blank', async () => {
        render(SampleImageGridItem, {
            props: {
                sample: { sample_id: 'image-1', annotations: [] } as unknown as ImageView,
                tileWidth: 240,
                tileHeight: 160
            }
        });
        expect(screen.queryByLabelText('No evaluation result')).not.toBeInTheDocument();
        imageSortBy.set([
            {
                source: 'evaluation_metric',
                evaluation_run_name: 'model',
                metric_name: 'fp',
                direction: 'desc'
            }
        ]);
        expect(await screen.findByLabelText('No evaluation result')).toHaveTextContent('—');
    });

    it('bounds annotation rendering to the image tile dimensions', () => {
        render(SampleImageGridItem, {
            props: {
                sample: { sample_id: 'image-1', annotations: [] } as unknown as ImageView,
                objectFit: 'cover',
                tileWidth: 240,
                tileHeight: 160
            }
        });

        expect(screen.getByTestId('mock-sample-annotations')).toHaveAttribute(
            'data-output-width',
            '240'
        );
        expect(screen.getByTestId('mock-sample-annotations')).toHaveAttribute(
            'data-output-height',
            '160'
        );
        expect(screen.getByTestId('mock-sample-annotations')).toHaveAttribute(
            'data-object-fit',
            'cover'
        );
    });
});
