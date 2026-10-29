import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import IncludeImagesOption from './IncludeImagesOption.svelte';
import { MAX_BROWSER_DOWNLOAD_BYTES, TOO_LARGE_REASON } from './includeImagesGate';

const { exportImagesEstimate } = vi.hoisted(() => ({ exportImagesEstimate: vi.fn() }));
vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    exportImagesEstimate
}));

const props = { collectionId: 'col-1', imageFilter: null, includeImages: true };

describe('IncludeImagesOption', () => {
    it('shows the image count and estimated size', async () => {
        exportImagesEstimate.mockResolvedValue({
            data: { image_count: 5000, estimated_bytes: 1.9 * 1024 ** 3 }
        });
        render(IncludeImagesOption, { props });

        expect(await screen.findByText('5,000 images, about 1.9 GB')).toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: 'Include images' })).toBeEnabled();
    });

    it('turns the option off above the browser download limit', async () => {
        exportImagesEstimate.mockResolvedValue({
            data: { image_count: 40000, estimated_bytes: MAX_BROWSER_DOWNLOAD_BYTES * 3 }
        });
        render(IncludeImagesOption, { props });

        expect(await screen.findByText(TOO_LARGE_REASON)).toBeInTheDocument();
        await waitFor(() =>
            expect(screen.getByRole('checkbox', { name: 'Include images' })).toBeDisabled()
        );
        expect(screen.getByRole('checkbox', { name: 'Include images' })).not.toBeChecked();
    });
});
