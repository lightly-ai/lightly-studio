import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { get } from 'svelte/store';
import { tick } from 'svelte';
import CombinedMetadataDimensionsFilters from './CombinedMetadataDimensionsFilters.svelte';
import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

const countsOptions = vi.fn();
vi.mock('$lib/components/CategoricalMetadataFilters', () => ({
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
    storage.updateMetadataInfo([]);
    useVideoFramesBounds().videoFramesBounds.set(null);
    useVideoFramesBounds().videoFramesBoundsValues.set(null);
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
        // Fields start collapsed, so the header shows the summary.
        expect(screen.getByText('2 – 10')).toBeInTheDocument();
        expect(screen.queryByRole('slider')).not.toBeInTheDocument();
    });

    it('hides the separator and disables Clear when no field is active', () => {
        render(CombinedMetadataDimensionsFilters, defaultProps);

        expect(screen.queryByTestId('metadata-active-separator')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Clear' })).toBeDisabled();
    });

    it('moves a field only when the pointer leaves the rows', async () => {
        const { container } = render(CombinedMetadataDimensionsFilters, defaultProps);
        const rows = screen.getByTestId('metadata-field-rows');
        const initialOrder = rowOrder(container);

        await fireEvent.pointerEnter(rows);
        narrowScore();
        await tick();
        expect(rowOrder(container)).toEqual(initialOrder);
        expect(screen.getByRole('checkbox', { name: 'score filter' })).toBeChecked();

        await fireEvent.pointerLeave(rows);
        expect(rowOrder(container).slice(0, 2)).toEqual(['numeric:score', '---']);
    });

    it('after keyboard input, moves a field only when the focus leaves the rows', async () => {
        const { container } = render(CombinedMetadataDimensionsFilters, defaultProps);
        const rows = screen.getByTestId('metadata-field-rows');
        const initialOrder = rowOrder(container);

        await fireEvent.keyDown(rows, { key: ' ' });
        narrowScore();
        await tick();
        expect(rowOrder(container)).toEqual(initialOrder);

        await fireEvent.focusOut(rows, { relatedTarget: document.body });
        expect(rowOrder(container)[0]).toBe('numeric:score');
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

        // The collapsed active field still needs its total.
        expect(screen.getByRole('button', { name: 'split' })).toHaveAttribute(
            'aria-expanded',
            'false'
        );
        expect(countsOptions).toHaveBeenLastCalledWith(
            expect.objectContaining({ fields: ['split'] })
        );
    });

    it('lists categorical fields for a video collection', async () => {
        const filter = { filter_type: 'video' as const };
        const { container } = render(CombinedMetadataDimensionsFilters, {
            ...defaultProps,
            isVideos: true,
            categoricalCountsFilter: filter
        });
        expect(container.querySelector('[data-field-id="categorical:split"]')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'split' }));
        expect(countsOptions).toHaveBeenCalledWith(
            expect.objectContaining({ filter, fields: ['split'] })
        );
    });

    it('lists no categorical fields for a video frame collection', () => {
        const { container } = render(CombinedMetadataDimensionsFilters, {
            ...defaultProps,
            isVideoFrames: true
        });
        expect(
            container.querySelector('[data-field-id="categorical:split"]')
        ).not.toBeInTheDocument();
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

    /** Opens the field and commits `text` as its minimum. */
    const commitMinimum = async (field: string, text: string) => {
        const toggle = screen.getByRole('button', { name: field });
        if (toggle.getAttribute('aria-expanded') === 'false') await fireEvent.click(toggle);
        const input = screen.getByRole('textbox', { name: `${field} minimum` });
        await fireEvent.input(input, { target: { value: text } });
        await fireEvent.blur(input);
        return input;
    };

    it.each([
        { type: 'float', max: 1, text: '0.123456789', sliderTick: '123' },
        { type: 'integer', max: 28_000_000, text: '12345', sliderTick: '4' }
    ] as const)(
        'commits an exact $type metadata value',
        async ({ type, max, text, sliderTick }) => {
            const bound = { min: 0, max };
            const storage = useGlobalStorage();
            storage.updateMetadataBounds({ score: bound });
            storage.updateMetadataValues({ score: bound });
            storage.updateMetadataInfo([{ name: 'score', type, ...bound }]);
            const onFilterChanged = vi.fn();
            render(CombinedMetadataDimensionsFilters, { ...defaultProps, onFilterChanged });

            const minimum = await commitMinimum('score', text);

            expect(get(storage.metadataValues).score).toEqual({ min: Number(text), max });
            expect(onFilterChanged).toHaveBeenCalledExactlyOnceWith('score', Number(text), max);
            expect(screen.getByRole('checkbox', { name: 'score filter' })).toBeChecked();
            expect(screen.getAllByRole('slider')[0]).toHaveAttribute('aria-valuenow', sliderTick);
            storage.updateMetadataValues({ score: bound });
            await tick();
            expect(minimum).toHaveValue('0');
        }
    );

    it('rejects a decimal value for an integer field', async () => {
        useGlobalStorage().updateMetadataInfo([
            { name: 'score', type: 'integer', min: 0, max: 10 }
        ]);
        const onFilterChanged = vi.fn();
        render(CombinedMetadataDimensionsFilters, { ...defaultProps, onFilterChanged });

        const minimum = await commitMinimum('score', '2.5');

        expect(minimum).toHaveAttribute('aria-invalid', 'true');
        expect(onFilterChanged).not.toHaveBeenCalled();
    });

    it.each(['width', 'height'] as const)('commits an exact image %s in pixels', async (key) => {
        const onFilterChanged = vi.fn();
        render(CombinedMetadataDimensionsFilters, { ...defaultProps, onFilterChanged });

        await commitMinimum(key === 'width' ? 'Width' : 'Height', '50');

        expect(get(useDimensions().dimensionsValues)?.[`min_${key}`]).toBe(50);
        expect(onFilterChanged).toHaveBeenCalledWith(key, 50, dimensionBounds[`max_${key}`]);
        const decimal = await commitMinimum(key === 'width' ? 'Width' : 'Height', '50.5');
        expect(decimal).toHaveAttribute('aria-invalid', 'true');
    });

    it('commits an exact frame number and follows slider changes', async () => {
        const bounds = { frame_number: { min: 0, max: 1000 } };
        useVideoFramesBounds().updateVideoFramesBounds(bounds);
        useVideoFramesBounds().updateVideoFramesBoundsValues(bounds);
        const onFilterChanged = vi.fn();
        render(CombinedMetadataDimensionsFilters, {
            ...defaultProps,
            categoricalKeys: [],
            isVideoFrames: true,
            onFilterChanged
        });

        const minimum = await commitMinimum('Frame number', '250');

        expect(get(useVideoFramesBounds().videoFramesBoundsValues)?.frame_number.min).toBe(250);
        expect(onFilterChanged).toHaveBeenCalledExactlyOnceWith('frame_number', 250, 1000);
        // The active frame number field is first, so its minimum thumb is the first slider.
        await fireEvent.keyDown(screen.getAllByRole('slider')[0], { key: 'ArrowRight' });
        expect(minimum).toHaveValue('251');
    });

    it.each([
        ['fps', 'FPS', '29.970029'],
        ['duration_s', 'Duration', '12.3456789']
    ] as const)('commits an exact video %s with decimals', async (key, label, text) => {
        const bounds = {
            ...videoBounds,
            fps: { min: 0, max: 60 },
            duration_s: { min: 0, max: 120 }
        };
        useVideoBounds().updateVideoBounds(bounds);
        useVideoBounds().updateVideoBoundsValues(bounds);
        const onFilterChanged = vi.fn();
        render(CombinedMetadataDimensionsFilters, {
            ...defaultProps,
            categoricalKeys: [],
            isVideos: true,
            onFilterChanged
        });

        await commitMinimum(label, text);

        expect(get(useVideoBounds().videoBoundsValues)?.[key].min).toBe(Number(text));
        expect(onFilterChanged).toHaveBeenCalledExactlyOnceWith(key, Number(text), bounds[key].max);
    });
});
