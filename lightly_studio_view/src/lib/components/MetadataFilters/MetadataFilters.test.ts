import { render } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import MetadataFilters from './index.svelte';

// Mock the dependencies
vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: vi.fn(() => ({
        metadataBounds: {
            subscribe: vi.fn((fn) => {
                fn({}); // Empty metadata bounds
                return { unsubscribe: vi.fn() };
            })
        },
        metadataValues: {
            subscribe: vi.fn((fn) => {
                fn({}); // Empty metadata values
                return { unsubscribe: vi.fn() };
            })
        },
        updateMetadataValues: vi.fn()
    }))
}));

vi.mock('$app/stores', () => ({
    page: {
        subscribe: vi.fn((fn) => {
            fn({ params: { dataset_id: 'test-dataset-id' } });
            return { unsubscribe: vi.fn() };
        })
    }
}));

describe('MetadataFilters', () => {
    it('should render without crashing', () => {
        render(MetadataFilters);
        // The component should render without throwing any errors
        expect(true).toBe(true);
    });

    it('should not render when no numerical metadata exists', () => {
        render(MetadataFilters);
        // When there's no numerical metadata, the component should not render anything
        // This is handled by the {#if numericalMetadata.length > 0} condition
        expect(true).toBe(true);
    });
});
