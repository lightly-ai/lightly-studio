import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { tick } from 'svelte';
import { useMetadataFilters } from '$lib/hooks';
import CombinedMetadataDimensionsFilters from './CombinedMetadataDimensionsFilters.svelte';

const storage = useMetadataFilters();
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
