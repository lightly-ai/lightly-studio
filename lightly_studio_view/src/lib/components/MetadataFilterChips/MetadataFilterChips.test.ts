import { render, screen, waitFor } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import MetadataFilterChips from './MetadataFilterChips.svelte';

const storage = useGlobalStorage();

const seed = ({ narrowed }: { narrowed: boolean }) => {
    storage.updateMetadataBounds({
        confidence: { min: 0, max: 1 },
        temperature: { min: 10, max: 40 }
    });
    storage.updateMetadataValues({
        confidence: narrowed ? { min: 0.25, max: 0.75 } : { min: 0, max: 1 },
        temperature: { min: 10, max: 40 }
    });
};

describe('MetadataFilterChips', () => {
    beforeEach(() => {
        storage.updateMetadataBounds({});
        storage.updateMetadataValues({});
    });

    it('renders nothing when no metadata filter is narrowed', () => {
        seed({ narrowed: false });
        render(MetadataFilterChips);

        expect(screen.queryByText('Metadata filters')).not.toBeInTheDocument();
    });

    it('shows a chip with the range for a narrowed filter only', () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        expect(screen.getByTestId('metadata-filter-chip-confidence')).toHaveTextContent(
            '0.25 – 0.75'
        );
        expect(screen.queryByTestId('metadata-filter-chip-temperature')).not.toBeInTheDocument();
        expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('unchecking resets the filter to the full bounds but keeps the chip', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        screen.getByRole('checkbox').click();

        await waitFor(() =>
            expect(get(storage.metadataValues).confidence).toEqual({ min: 0, max: 1 })
        );
        // The chip stays (remembering the range) and is now unchecked.
        expect(screen.getByTestId('metadata-filter-chip-confidence')).toHaveTextContent(
            '0.25 – 0.75'
        );
        expect(screen.getByRole('checkbox')).not.toBeChecked();
    });

    it('re-checking restores the remembered range', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        screen.getByRole('checkbox').click();
        await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked());

        screen.getByRole('checkbox').click();

        await waitFor(() =>
            expect(get(storage.metadataValues).confidence).toEqual({ min: 0.25, max: 0.75 })
        );
        expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('clearing resets the filter and removes the chip', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        screen.getByLabelText('Clear confidence').click();

        await waitFor(() =>
            expect(get(storage.metadataValues).confidence).toEqual({ min: 0, max: 1 })
        );
        await waitFor(() =>
            expect(screen.queryByTestId('metadata-filter-chip-confidence')).not.toBeInTheDocument()
        );
    });
});
