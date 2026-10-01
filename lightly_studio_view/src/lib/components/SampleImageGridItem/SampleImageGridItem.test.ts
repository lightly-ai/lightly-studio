import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { ImageView } from '$lib/api/lightly_studio_local';
import SampleImageGridItem from './SampleImageGridItem.svelte';

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
