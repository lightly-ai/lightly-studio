const { trackEvent } = vi.hoisted(() => ({ trackEvent: vi.fn() }));
vi.mock('$lib/hooks', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/hooks')>()),
    usePostHog: () => ({ trackEvent })
}));

import { render, screen, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useFiltersClearedSignal } from '$lib/hooks';
import { useDimensions } from '$lib/hooks';
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
        trackEvent.mockClear();
        storage.updateCategoricalMetadataValues({});
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

    it('removes remembered chips when all filters are cleared', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        storage.updateMetadataValues({
            confidence: { min: 0, max: 1 },
            temperature: { min: 10, max: 40 }
        });
        useFiltersClearedSignal().signalFiltersCleared();

        await waitFor(() =>
            expect(screen.queryByTestId('metadata-filter-chip-confidence')).not.toBeInTheDocument()
        );
    });

    it('removes chips when the clear-all signal fires before the values are reset', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);
        expect(screen.getByTestId('metadata-filter-chip-confidence')).toBeInTheDocument();

        useFiltersClearedSignal().signalFiltersCleared();
        await tick();
        storage.updateMetadataValues({
            confidence: { min: 0, max: 1 },
            temperature: { min: 10, max: 40 }
        });
        await tick();

        expect(screen.queryByTestId('metadata-filter-chip-confidence')).not.toBeInTheDocument();
    });

    it('removes categorical chips when the clear-all signal fires before the values are reset', async () => {
        storage.updateCategoricalMetadataValues({ city: ['Berlin'] });
        render(MetadataFilterChips);
        expect(screen.getByTestId('metadata-filter-chip-city')).toBeInTheDocument();

        useFiltersClearedSignal().signalFiltersCleared();
        await tick();
        storage.updateCategoricalMetadataValues({});
        await tick();

        expect(screen.queryByTestId('metadata-filter-chip-city')).not.toBeInTheDocument();
    });

    describe('dimension chips', () => {
        const full = { min_width: 10, max_width: 100, min_height: 20, max_height: 200 };
        const { updateDimensionsBounds, updateDimensionsValues } = useDimensions();

        beforeEach(() => {
            updateDimensionsBounds(full);
            updateDimensionsValues({ ...full, min_width: 50, max_height: 150 });
        });

        it('shows width and height chips next to numeric and categorical chips', () => {
            seed({ narrowed: true });
            storage.updateCategoricalMetadataValues({ city: ['Berlin'] });
            render(MetadataFilterChips, { props: { showDimensions: true } });

            expect(screen.getByTestId('metadata-filter-chip-image-width')).toHaveTextContent(
                '50 – 100px'
            );
            expect(screen.getByTestId('metadata-filter-chip-image-height')).toHaveTextContent(
                '20 – 150px'
            );
            expect(screen.getByTestId('metadata-filter-chip-confidence')).toBeInTheDocument();
            expect(screen.getByTestId('metadata-filter-chip-city')).toBeInTheDocument();
        });

        it('hides width and height chips unless showDimensions is set', () => {
            render(MetadataFilterChips);

            expect(
                screen.queryByTestId('metadata-filter-chip-image-width')
            ).not.toBeInTheDocument();
        });

        it('clearing the width chip resets the width filter', async () => {
            render(MetadataFilterChips, { props: { showDimensions: true } });

            screen.getByLabelText('Clear width').click();

            await waitFor(() =>
                expect(
                    screen.queryByTestId('metadata-filter-chip-image-width')
                ).not.toBeInTheDocument()
            );
            expect(get(useDimensions().dimensionsValues)).toEqual({ ...full, max_height: 150 });
        });
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

    const defaultProps = { collectionId: 'col-1' };

    it('fires metadata_filter_changed with action disabled when unchecking', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips, { props: defaultProps });

        screen.getByRole('checkbox').click();

        await waitFor(() =>
            expect(trackEvent).toHaveBeenCalledWith('metadata_filter_changed', {
                collection_id: 'col-1',
                field_name: 'confidence',
                action: 'disabled'
            })
        );
    });

    it('fires metadata_filter_changed with action enabled when re-checking', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips, { props: defaultProps });

        screen.getByRole('checkbox').click();
        await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked());
        trackEvent.mockClear();

        screen.getByRole('checkbox').click();

        await waitFor(() =>
            expect(trackEvent).toHaveBeenCalledWith('metadata_filter_changed', {
                collection_id: 'col-1',
                field_name: 'confidence',
                action: 'enabled'
            })
        );
    });

    it('fires metadata_filter_changed with action disabled when clearing', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips, { props: defaultProps });

        screen.getByLabelText('Clear confidence').click();

        await waitFor(() =>
            expect(trackEvent).toHaveBeenCalledWith('metadata_filter_changed', {
                collection_id: 'col-1',
                field_name: 'confidence',
                action: 'disabled'
            })
        );
    });

    it('does not fire metadata_filter_changed when collectionId is not provided', async () => {
        seed({ narrowed: true });
        render(MetadataFilterChips);

        screen.getByRole('checkbox').click();

        await waitFor(() =>
            expect(get(storage.metadataValues).confidence).toEqual({ min: 0, max: 1 })
        );
        expect(trackEvent).not.toHaveBeenCalled();
    });

    it('renders categorical selections as chips like numeric filters', () => {
        storage.updateCategoricalMetadataValues({ location_type: ['city', 'rural'] });
        render(MetadataFilterChips, { props: { collectionId: 'col-1' } });

        expect(screen.getByTestId('metadata-filter-chip-location_type')).toBeInTheDocument();
    });
});
