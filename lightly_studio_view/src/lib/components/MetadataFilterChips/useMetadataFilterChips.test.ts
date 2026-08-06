const { trackEvent } = vi.hoisted(() => ({ trackEvent: vi.fn() }));
vi.mock('$lib/hooks', () => ({
    usePostHog: () => ({ trackEvent })
}));

import { render, screen, waitFor } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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

    describe('categorical metadata', () => {
        it('shows a chip when categorical values are selected', () => {
            storage.updateCategoricalMetadataValues({ location_type: ['city', 'rural'] });
            render(MetadataFilterChips);

            expect(screen.getByTestId('metadata-filter-chip-location_type')).toBeInTheDocument();
        });

        it('chip subtitle shows the selected values joined by comma', () => {
            storage.updateCategoricalMetadataValues({ location_type: ['city', 'rural'] });
            render(MetadataFilterChips);

            expect(screen.getByTestId('metadata-filter-chip-location_type')).toHaveTextContent(
                'city, rural'
            );
        });

        it('chip is checked when values are active', () => {
            storage.updateCategoricalMetadataValues({ location_type: ['city'] });
            render(MetadataFilterChips);

            expect(screen.getByRole('checkbox')).toBeChecked();
        });

        it('does not show a chip when categorical values are empty', () => {
            storage.updateCategoricalMetadataValues({ location_type: [] });
            render(MetadataFilterChips);

            expect(
                screen.queryByTestId('metadata-filter-chip-location_type')
            ).not.toBeInTheDocument();
        });

        it('unchecking clears the filter but keeps the chip with the remembered values', async () => {
            storage.updateCategoricalMetadataValues({ location_type: ['city', 'rural'] });
            render(MetadataFilterChips);

            screen.getByRole('checkbox').click();

            await waitFor(() =>
                expect(get(storage.categoricalMetadataValues).location_type).toEqual([])
            );
            expect(screen.getByTestId('metadata-filter-chip-location_type')).toHaveTextContent(
                'city, rural'
            );
            expect(screen.getByRole('checkbox')).not.toBeChecked();
        });

        it('re-checking restores the remembered categorical values', async () => {
            storage.updateCategoricalMetadataValues({ location_type: ['city', 'rural'] });
            render(MetadataFilterChips);

            screen.getByRole('checkbox').click();
            await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked());

            screen.getByRole('checkbox').click();

            await waitFor(() =>
                expect(get(storage.categoricalMetadataValues).location_type).toEqual([
                    'city',
                    'rural'
                ])
            );
            expect(screen.getByRole('checkbox')).toBeChecked();
        });

        it('clearing removes the chip and the filter', async () => {
            storage.updateCategoricalMetadataValues({ location_type: ['city'] });
            render(MetadataFilterChips);

            screen.getByLabelText('Clear location_type').click();

            await waitFor(() =>
                expect(
                    screen.queryByTestId('metadata-filter-chip-location_type')
                ).not.toBeInTheDocument()
            );
            expect(get(storage.categoricalMetadataValues).location_type).toBeUndefined();
        });

        it('formats null as "Missing"', () => {
            storage.updateCategoricalMetadataValues({ location_type: [null] });
            render(MetadataFilterChips);

            expect(screen.getByTestId('metadata-filter-chip-location_type')).toHaveTextContent(
                'Missing'
            );
        });

        it('disambiguates null and the string "Missing" when both are selected', () => {
            storage.updateCategoricalMetadataValues({ location_type: [null, 'Missing'] });
            render(MetadataFilterChips);

            expect(screen.getByTestId('metadata-filter-chip-location_type')).toHaveTextContent(
                'Missing (no value), Missing (value)'
            );
        });
    });
});
