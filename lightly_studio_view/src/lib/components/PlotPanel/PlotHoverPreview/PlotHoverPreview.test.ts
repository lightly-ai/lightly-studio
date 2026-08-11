import { render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import PlotHoverPreview from './PlotHoverPreview.svelte';

class MockImage {
    static instances: MockImage[] = [];
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    naturalWidth = 640;
    naturalHeight = 480;
    src = '';
    constructor() {
        MockImage.instances.push(this);
    }
}

beforeEach(() => {
    MockImage.instances = [];
    vi.stubGlobal('Image', MockImage);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('PlotHoverPreview', () => {
    it('shows a spinner while loading and swaps to the image once loaded', async () => {
        render(PlotHoverPreview, {
            props: {
                sampleId: 'sample-a',
                resolveThumbnail: () => Promise.resolve({ url: 'https://example.com/thumb.jpg' })
            }
        });

        expect(screen.getByRole('status')).toBeInTheDocument();
        expect(screen.queryByRole('img')).not.toBeInTheDocument();

        await waitFor(() => expect(MockImage.instances).toHaveLength(1));
        MockImage.instances[0].onload?.();

        const image = await screen.findByRole('img');
        expect(image).toHaveAttribute('src', 'https://example.com/thumb.jpg');
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    it('positions annotation images and bounding boxes around the padded crop region', async () => {
        const annotation = {
            parent_sample_id: 'parent-a',
            sample_id: 'annotation-a',
            annotation_collection_id: 'collection-a',
            annotation_type: 'object_detection' as const,
            annotation_label: { annotation_label_name: 'car' },
            created_at: new Date(),
            object_detection_details: { x: 10, y: 20, width: 30, height: 40 }
        };
        const { container } = render(PlotHoverPreview, {
            props: {
                sampleId: 'annotation-a',
                resolveThumbnail: () =>
                    Promise.resolve({
                        url: 'https://example.com/full-image.jpg',
                        annotation
                    })
            }
        });

        await waitFor(() => expect(MockImage.instances).toHaveLength(1));
        MockImage.instances[0].onload?.();

        const preview = screen.getByTestId('plot-hover-preview');
        expect(preview).toHaveClass('relative', 'overflow-hidden');
        await waitFor(() => expect(container.querySelector('.crop')).not.toBeNull());
        const crop = container.querySelector('.crop');
        expect(crop).toHaveStyle({ backgroundImage: 'url(https://example.com/full-image.jpg)' });
        const annotationBox = container.querySelector('.annotation-box');
        expect(annotationBox).toHaveStyle({
            left: '40px',
            top: '32px',
            width: '48px',
            height: '64px'
        });
    });

    it('renders nothing when the thumbnail cannot be resolved', async () => {
        render(PlotHoverPreview, {
            props: {
                sampleId: 'sample-a',
                resolveThumbnail: () => Promise.resolve(null)
            }
        });

        await waitFor(() =>
            expect(screen.queryByTestId('plot-hover-preview')).not.toBeInTheDocument()
        );
    });
});
