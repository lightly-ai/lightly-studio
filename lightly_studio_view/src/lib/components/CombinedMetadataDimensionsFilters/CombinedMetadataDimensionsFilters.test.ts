import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { tick } from 'svelte';
import { useDimensions, useMetadataFilters, useVideoFramesBounds } from '$lib/hooks';
import CombinedMetadataDimensionsFilters from './CombinedMetadataDimensionsFilters.svelte';

const storage = useMetadataFilters();
const dimensions = useDimensions();
const frames = useVideoFramesBounds();
vi.mock('$app/state', () => ({ page: { params: {} } }));
const defaultProps = {
    collectionId: '',
    showDimensions: false,
    onCategoricalValueToggle: vi.fn(),
    onCategoricalValuesClear: vi.fn()
};
afterEach(() => {
    storage.updateMetadataBounds({});
    storage.updateMetadataValues({});
    storage.updateMetadataInfo([]);
    dimensions.updateDimensionsBounds({ min_width: 0, max_width: 0, min_height: 0, max_height: 0 });
    dimensions.updateDimensionsValues({ min_width: 0, max_width: 0, min_height: 0, max_height: 0 });
    frames.videoFramesBounds.set(null);
    frames.videoFramesBoundsValues.set(null);
});

it.each([
    { type: 'float', max: 1, input: '0.123456789' },
    { type: 'integer', max: 28_000_000, input: '12345' }
] as const)(
    'commits exact $type metadata and synchronizes sliders and resets',
    async ({ type, max, input }) => {
        const bound = { min: 0, max };
        storage.updateMetadataBounds({ score: bound });
        storage.updateMetadataValues({ score: bound });
        storage.updateMetadataInfo([{ name: 'score', type, ...bound }]);
        const onFilterChanged = vi.fn();
        render(CombinedMetadataDimensionsFilters, { ...defaultProps, onFilterChanged });
        const minimum = screen.getByRole('textbox', { name: 'score minimum' });
        await fireEvent.input(minimum, { target: { value: input } });
        await fireEvent.blur(minimum);
        const min = Number(input);
        expect(get(storage.metadataValues).score).toEqual({ min, max });
        expect(storage.createMetadataFilters(get(storage.metadataValues))).toEqual([
            { key: 'score', value: min, op: '>=' }
        ]);
        expect(onFilterChanged).toHaveBeenCalledExactlyOnceWith('score', min, max);
        expect(screen.getAllByRole('slider')[0]).toHaveAttribute(
            'aria-valuenow',
            type === 'float' ? '123' : '4'
        );
        if (type === 'integer') {
            await fireEvent.input(minimum, { target: { value: '12345.5' } });
            await fireEvent.blur(minimum);
            expect(minimum).toHaveAttribute('aria-invalid', 'true');
            expect(onFilterChanged).toHaveBeenCalledTimes(1);
        }
        storage.updateMetadataValues({ score: bound });
        await tick();
        expect(minimum).toHaveValue('0');
        expect(storage.createMetadataFilters(get(storage.metadataValues))).toEqual([]);
    }
);

it.each(['width', 'height'] as const)('edits image %s in exact pixels', async (field) => {
    const bounds = { min_width: 0, max_width: 1000, min_height: 0, max_height: 1000 };
    dimensions.updateDimensionsBounds(bounds);
    dimensions.updateDimensionsValues({ ...bounds, [`min_${field}`]: 257 });
    const onFilterChanged = vi.fn();
    render(CombinedMetadataDimensionsFilters, {
        ...defaultProps,
        showDimensions: true,
        onFilterChanged
    });
    const input = screen.getByRole('textbox', { name: new RegExp(`${field} minimum`, 'i') });
    await fireEvent.input(input, { target: { value: '250' } });
    await fireEvent.blur(input);
    expect(get(dimensions.dimensionsValues)).toEqual({ ...bounds, [`min_${field}`]: 250 });
    expect(onFilterChanged).toHaveBeenCalledExactlyOnceWith(field, 250, 1000);
    await fireEvent.input(input, { target: { value: '250.5' } });
    await fireEvent.blur(input);
    expect(input).toHaveAttribute('aria-invalid', 'true');
    dimensions.updateDimensionsValues(bounds);
    await tick();
    expect(input).toHaveValue('0');
});

it('edits exact frame numbers and synchronizes slider changes', async () => {
    const bounds = { frame_number: { min: 0, max: 1000 } };
    frames.updateVideoFramesBounds(bounds);
    frames.updateVideoFramesBoundsValues(bounds);
    const onFilterChanged = vi.fn();
    render(CombinedMetadataDimensionsFilters, {
        ...defaultProps,
        isVideoFrames: true,
        onFilterChanged
    });
    const input = screen.getByRole('textbox', { name: 'Frame number minimum' });
    await fireEvent.input(input, { target: { value: '250' } });
    await fireEvent.blur(input);
    expect(get(frames.videoFramesBoundsValues)?.frame_number.min).toBe(250);
    expect(onFilterChanged).toHaveBeenCalledExactlyOnceWith('frame_number', 250, 1000);
    await fireEvent.keyDown(screen.getAllByRole('slider')[0], { key: 'ArrowRight' });
    expect(input).toHaveValue('251');
});
