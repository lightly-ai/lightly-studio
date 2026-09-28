import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CombinedMetadataDimensionsFilters from './CombinedMetadataDimensionsFilters.svelte';

const metadataBounds = writable({ score: { min: 0, max: 10 } });
const metadataValues = writable({ score: { min: 0, max: 10 } });
const categoricalMetadataValues = writable<Record<string, string[]>>({});

vi.mock('$app/state', () => ({ page: { params: { collection_id: 'collection-id' } } }));
vi.mock('$lib/hooks/useDimensions/useDimensions', () => ({
    useDimensions: () => ({
        dimensionsBounds: writable(null),
        dimensionsValues: writable(null),
        updateDimensionsValues: vi.fn()
    })
}));
vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataBounds,
        metadataValues,
        categoricalMetadataValues,
        updateMetadataValues: metadataValues.set,
        updateCategoricalMetadataValues: categoricalMetadataValues.set
    })
}));

describe('CombinedMetadataDimensionsFilters', () => {
    beforeEach(() => {
        metadataValues.set({ score: { min: 0, max: 10 } });
        categoricalMetadataValues.set({});
    });

    it('shows categorical fields on demand and clears their filters when removed', async () => {
        const onCategoricalValueToggle = vi.fn();
        render(CombinedMetadataDimensionsFilters, {
            props: {
                isImageCollection: true,
                categoricalKeys: ['location'],
                categoricalDistributions: {
                    location: [
                        { id: 'city', kind: 'value', value: 'city', label: 'city', count: 3 },
                        { id: 'rural', kind: 'value', value: 'rural', label: 'rural', count: 2 }
                    ]
                },
                onCategoricalValueToggle
            }
        });

        expect(screen.queryByText('score')).toBeNull();
        expect(screen.queryByRole('heading', { name: 'location' })).toBeNull();

        await fireEvent.click(
            screen.getByRole('button', { name: 'Add categorical metadata field' })
        );
        await fireEvent.click(screen.getByRole('button', { name: 'location' }));

        const field = screen.getByTestId('metadata-categorical-filter');
        expect(within(field).getByRole('heading', { name: 'location' })).toBeVisible();
        await fireEvent.click(within(field).getByTestId('metadata-categorical-filter-trigger'));
        expect(screen.getByText('city')).toBeVisible();
        expect(screen.getByText('rural')).toBeVisible();
        await fireEvent.click(
            screen.getByRole('checkbox', { name: 'Select value city, 3 samples' })
        );
        expect(onCategoricalValueToggle).toHaveBeenCalledWith('location', 'city');

        categoricalMetadataValues.set({ location: ['city'] });
        await fireEvent.click(
            screen.getByRole('button', { name: 'Remove metadata field location' })
        );
        expect(screen.queryByRole('heading', { name: 'location' })).toBeNull();
        expect(get(categoricalMetadataValues)).toEqual({});
        expect(screen.queryByText('score')).toBeNull();
    });

    it('shows categorical fields with active filters', () => {
        categoricalMetadataValues.set({ location: ['rural'] });
        render(CombinedMetadataDimensionsFilters, {
            props: { isImageCollection: true, categoricalKeys: ['location'] }
        });

        expect(screen.getByRole('heading', { name: 'location' })).toBeVisible();
    });
});
