import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { get } from 'svelte/store';
import CombinedMetadataDimensionsFilters from './CombinedMetadataDimensionsFilters.svelte';
import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

const countsOptions = vi.fn();
vi.mock('$lib/components/CategoricalMetadataFilters/useCategoricalFieldCounts.svelte', () => ({
    useCategoricalFieldCounts: (getOptions: () => unknown) => ({
        get distributions() {
            countsOptions(getOptions());
            return {};
        },
        loading: false,
        updating: false,
        error: undefined,
        refetch: vi.fn()
    })
}));
vi.mock('$lib/hooks', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/hooks')>()),
    usePostHog: () => ({ trackEvent: vi.fn() })
}));
vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local')>()),
    getMetadataInfo: vi.fn(() => Promise.resolve({ data: undefined })),
    getFieldsBounds: vi.fn(() => Promise.resolve({ data: undefined })),
    getVideoFramesFieldsBounds: vi.fn(() => Promise.resolve({ data: undefined }))
}));
vi.mock('$lib/services/loadDimensionBounds', () => ({
    loadDimensionBounds: vi.fn(() => Promise.resolve({ data: undefined }))
}));

const dimensionBounds = { min_width: 10, max_width: 100, min_height: 20, max_height: 200 };
const videoBounds = {
    width: { min: 1, max: 5 },
    height: { min: 2, max: 6 },
    duration_s: { min: 0, max: 9 },
    fps: { min: 30, max: 30 }
};

const defaultProps = {
    collectionId: 'collection-1',
    categoricalKeys: ['split'],
    onCategoricalValueToggle: vi.fn(),
    onCategoricalValuesSet: vi.fn(),
    onCategoricalValuesClear: vi.fn()
};

const rowOrder = (container: HTMLElement) =>
    Array.from(
        container.querySelectorAll('[data-field-id], [data-testid="metadata-active-separator"]')
    ).map((element) => element.getAttribute('data-field-id') ?? '---');

const narrowScore = () => useGlobalStorage().updateMetadataValues({ score: { min: 2, max: 10 } });

beforeEach(() => {
    countsOptions.mockClear();
    const storage = useGlobalStorage();
    storage.updateMetadataBounds({ score: { min: 0, max: 10 } });
    storage.updateMetadataValues({ score: { min: 0, max: 10 } });
    storage.updateCategoricalMetadataValues({});
    useDimensions().updateDimensionsBounds(dimensionBounds);
    useDimensions().updateDimensionsValues(dimensionBounds);
    useVideoBounds().updateVideoBounds(videoBounds);
    useVideoBounds().updateVideoBoundsValues(videoBounds);
});

describe('CombinedMetadataDimensionsFilters', () => {
    it('renders active fields first with a separator', () => {
        narrowScore();
        const { container } = render(CombinedMetadataDimensionsFilters, defaultProps);

        expect(rowOrder(container)).toEqual([
            'numeric:score',
            '---',
            'dimension:width',
            'dimension:height',
            'categorical:split'
        ]);
        expect(screen.getByRole('checkbox', { name: 'score filter' })).toBeChecked();
        // The field is expanded, so its slider shows the range instead of the summary.
        expect(screen.queryByText('2 – 10')).not.toBeInTheDocument();
    });

    it('hides the separator and disables Clear when no field is active', () => {
        render(CombinedMetadataDimensionsFilters, defaultProps);

        expect(screen.queryByTestId('metadata-active-separator')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Clear' })).toBeDisabled();
    });

    it('hides the separator when every field is active', () => {
        narrowScore();
        useDimensions().updateDimensionsValues({
            ...dimensionBounds,
            min_width: 20,
            max_height: 100
        });
        useGlobalStorage().updateCategoricalMetadataValues({ split: ['train'] });
        render(CombinedMetadataDimensionsFilters, defaultProps);

        expect(screen.queryByTestId('metadata-active-separator')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Clear' })).toBeEnabled();
    });

    it('Clear resets all fields', async () => {
        narrowScore();
        useDimensions().updateDimensionsValues({ ...dimensionBounds, min_width: 20 });
        useGlobalStorage().updateCategoricalMetadataValues({ split: ['train'] });
        render(CombinedMetadataDimensionsFilters, defaultProps);

        await fireEvent.click(screen.getByRole('button', { name: 'Clear' }));

        expect(get(useGlobalStorage().metadataValues).score).toEqual({ min: 0, max: 10 });
        expect(get(useDimensions().dimensionsValues)).toEqual(dimensionBounds);
        expect(get(useGlobalStorage().categoricalMetadataValues)).toEqual({});
        for (const name of ['score filter', 'Width filter', 'split filter']) {
            expect(screen.getByRole('checkbox', { name })).not.toBeChecked();
        }
        expect(screen.getByRole('button', { name: 'Clear' })).toBeDisabled();
    });

    it('unchecking a row resets only that field', async () => {
        narrowScore();
        useDimensions().updateDimensionsValues({ ...dimensionBounds, min_width: 20 });
        render(CombinedMetadataDimensionsFilters, defaultProps);

        await fireEvent.click(screen.getByRole('checkbox', { name: 'score filter' }));

        expect(get(useGlobalStorage().metadataValues).score).toEqual({ min: 0, max: 10 });
        expect(get(useDimensions().dimensionsValues)?.min_width).toBe(20);
        expect(screen.getByRole('checkbox', { name: 'Width filter' })).toBeChecked();
    });

    it('search result keeps the active-first order', async () => {
        const keys = ['alpha_1', 'alpha_2', 'beta_1', 'beta_2', 'beta_3', 'gamma', 'delta'];
        const storage = useGlobalStorage();
        storage.updateMetadataBounds(Object.fromEntries(keys.map((k) => [k, { min: 0, max: 10 }])));
        storage.updateMetadataValues({
            ...Object.fromEntries(keys.map((k) => [k, { min: 0, max: 10 }])),
            alpha_2: { min: 5, max: 10 }
        });
        const { container } = render(CombinedMetadataDimensionsFilters, defaultProps);

        const search = screen.getByRole('textbox', { name: 'Search metadata fields' });
        await fireEvent.input(search, { target: { value: 'alpha' } });

        expect(rowOrder(container)).toEqual(['numeric:alpha_2', '---', 'numeric:alpha_1']);
        const marks = [...container.querySelectorAll('mark')].map((mark) => mark.textContent);
        expect(marks).toEqual(['alpha', 'alpha']);
    });

    it('keeps the list height while searching so the search box does not move', async () => {
        const keys = ['alpha_1', 'alpha_2', 'beta_1', 'beta_2', 'beta_3', 'gamma', 'delta'];
        const storage = useGlobalStorage();
        storage.updateMetadataBounds(Object.fromEntries(keys.map((k) => [k, { min: 0, max: 10 }])));
        storage.updateMetadataValues(Object.fromEntries(keys.map((k) => [k, { min: 0, max: 10 }])));
        const height = vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(400);
        const { container } = render(CombinedMetadataDimensionsFilters, defaultProps);
        const rows = container.querySelector('[data-field-id]')!.parentElement!;
        const search = screen.getByRole('textbox', { name: 'Search metadata fields' });

        await fireEvent.input(search, { target: { value: 'alpha' } });
        expect(rows.style.minHeight).toBe('400px');

        await fireEvent.input(search, { target: { value: '' } });
        expect(rows.style.minHeight).toBe('');
        height.mockRestore();
    });

    it('requests value counts for a collapsed active categorical field', () => {
        const keys = ['k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'k7'];
        const storage = useGlobalStorage();
        storage.updateMetadataBounds(Object.fromEntries(keys.map((k) => [k, { min: 0, max: 10 }])));
        storage.updateMetadataValues(Object.fromEntries(keys.map((k) => [k, { min: 0, max: 10 }])));
        storage.updateCategoricalMetadataValues({ split: ['train'] });
        render(CombinedMetadataDimensionsFilters, defaultProps);

        // More than 8 fields start collapsed; the active field still needs its total.
        expect(screen.getByRole('button', { name: 'split' })).toHaveAttribute(
            'aria-expanded',
            'false'
        );
        expect(countsOptions).toHaveBeenLastCalledWith(
            expect.objectContaining({ fields: ['split'] })
        );
    });

    it('lists categorical fields for a video collection', () => {
        const filter = { filter_type: 'video' as const };
        const { container } = render(CombinedMetadataDimensionsFilters, {
            ...defaultProps,
            isVideos: true,
            categoricalCountsFilter: filter
        });
        expect(container.querySelector('[data-field-id="categorical:split"]')).toBeInTheDocument();
        expect(countsOptions).toHaveBeenCalledWith(
            expect.objectContaining({ filter, fields: ['split'] })
        );
    });

    it('lists video fields with checkboxes and no image dimensions', () => {
        const { container } = render(CombinedMetadataDimensionsFilters, {
            ...defaultProps,
            categoricalKeys: [],
            isVideos: true
        });

        expect(rowOrder(container)).toEqual([
            'video:width',
            'video:height',
            'video:duration_s',
            'numeric:score'
        ]);
        expect(screen.getByRole('checkbox', { name: 'Duration filter' })).not.toBeChecked();
    });
});
