import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import JumpToDuplicateSample from './JumpToDuplicateSample.svelte';

vi.mock('$app/state', () => ({
    page: {
        params: {
            collection_type: 'video',
            collection_id: 'collection-1'
        }
    }
}));

vi.mock('$lib/routes', () => ({
    routeHelpers: {
        toVideosDetails: vi.fn(
            ({ sampleId }: { sampleId: string }) => `/videos/${sampleId}`
        )
    }
}));

describe('JumpToDuplicateSample', () => {
    it('renders a link to the kept sample when duplicate_of metadata is set', () => {
        render(JumpToDuplicateSample, {
            props: {
                datasetId: 'dataset-1',
                metadataDict: { data: { duplicate_of: 'kept-sample-id' } }
            }
        });

        const button = screen.getByTestId('jump-to-duplicate-sample-button');
        expect(button).toHaveAttribute('href', '/videos/kept-sample-id');
        expect(button).toHaveTextContent('Jump to kept sample');
    });

    it('renders nothing when duplicate_of metadata is missing', () => {
        render(JumpToDuplicateSample, {
            props: {
                datasetId: 'dataset-1',
                metadataDict: { data: {} }
            }
        });

        expect(screen.queryByTestId('jump-to-duplicate-sample-button')).toBeNull();
    });
});
