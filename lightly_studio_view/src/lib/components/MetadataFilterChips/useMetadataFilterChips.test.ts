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

describe('useMetadataFilterChips', () => {
    beforeEach(() => {
        storage.updateMetadataBounds({});
        storage.updateMetadataValues({});
    });

    it('provides a chip only for narrowed filters, not for full-range ones', () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        expect(screen.getByTestId('metadata-filter-chip-confidence')).toBeInTheDocument();
        expect(screen.queryByTestId('metadata-filter-chip-temperature')).not.toBeInTheDocument();
    });

    it('chip shows the active range and is checked', () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        expect(screen.getByTestId('metadata-filter-chip-confidence')).toHaveTextContent(
            '0.25 – 0.75'
        );
        expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('unchecking resets the filter to bounds but keeps chip with the remembered range', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        screen.getByRole('checkbox').click();

        await waitFor(() =>
            expect(get(storage.metadataValues).confidence).toEqual({ min: 0, max: 1 })
        );
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

    it('formats integer bounds without decimal places', () => {
        storage.updateMetadataBounds({ count: { min: 0, max: 100 } });
        storage.updateMetadataValues({ count: { min: 5, max: 80 } });
        render(MetadataFilterChips);

        expect(screen.getByTestId('metadata-filter-chip-count')).toHaveTextContent('5 – 80');
    });

    it('formats float bounds with decimal places', () => {
        storage.updateMetadataBounds({ score: { min: 0.5, max: 1.5 } });
        storage.updateMetadataValues({ score: { min: 0.75, max: 1.25 } });
        render(MetadataFilterChips);

        expect(screen.getByTestId('metadata-filter-chip-score')).toHaveTextContent('0.75 – 1.25');
    });
});
