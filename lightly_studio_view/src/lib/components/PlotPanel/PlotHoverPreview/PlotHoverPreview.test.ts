import { render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import PlotHoverPreview from './PlotHoverPreview.svelte';

class MockImage {
    static instances: MockImage[] = [];
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
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
                resolveThumbnailUrl: () => Promise.resolve('https://example.com/thumb.jpg')
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

    it('renders nothing when the thumbnail cannot be resolved', async () => {
        render(PlotHoverPreview, {
            props: {
                sampleId: 'sample-a',
                resolveThumbnailUrl: () => Promise.resolve(null)
            }
        });

        await waitFor(() =>
            expect(screen.queryByTestId('plot-hover-preview')).not.toBeInTheDocument()
        );
    });
});
