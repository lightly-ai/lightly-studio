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

    it('prettifies underscore-separated keys as chip titles', async () => {
        storage.updateMetadataBounds({ my_score: { min: 0, max: 1 } });
        storage.updateMetadataValues({ my_score: { min: 0.1, max: 0.9 } });
        render(MetadataFilterChips);
        expect(await screen.findByText('my score')).toBeInTheDocument();
    });
});
