import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import MetadataFilterChips from './MetadataFilterChips.svelte';

const storage = useGlobalStorage();

describe('MetadataFilterChips', () => {
    beforeEach(() => {
        storage.updateMetadataBounds({});
        storage.updateMetadataValues({});
    });

    it('renders nothing when no filter is narrowed', () => {
        storage.updateMetadataBounds({ confidence: { min: 0, max: 1 } });
        storage.updateMetadataValues({ confidence: { min: 0, max: 1 } });
        render(MetadataFilterChips);
        expect(screen.queryByText('Metadata filters')).not.toBeInTheDocument();
    });
});
