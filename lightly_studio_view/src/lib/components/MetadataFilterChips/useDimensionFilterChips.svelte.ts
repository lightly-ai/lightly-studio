import { fromStore } from 'svelte/store';
import { useDimensions } from '$lib/hooks';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { useRangeChips } from './useRangeChips.svelte';

type RangeChipsParams = Parameters<typeof useRangeChips>[0];
type RangeMap = ReturnType<RangeChipsParams['getBounds']>;
type Range = Parameters<RangeChipsParams['setRange']>[1];

const toRanges = (dimensions: DimensionBounds | null): RangeMap =>
    dimensions
        ? {
              width: { min: dimensions.min_width, max: dimensions.max_width },
              height: { min: dimensions.min_height, max: dimensions.max_height }
          }
        : {};

/** Chips for the image width and height filters, with the metadata chip behaviour. */
export function useDimensionFilterChips(): ReturnType<typeof useRangeChips> {
    const { dimensionsBounds, dimensionsValues, updateDimensionsValues } = useDimensions();
    const bounds = fromStore(dimensionsBounds);
    const values = fromStore(dimensionsValues);

    const setRange = (key: string, range: Range) => {
        const current = values.current;
        if (!current) return;
        updateDimensionsValues(
            key === 'width'
                ? { ...current, min_width: range.min, max_width: range.max }
                : { ...current, min_height: range.min, max_height: range.max }
        );
    };

    return useRangeChips({
        getBounds: () => toRanges(bounds.current),
        getValues: () => toRanges(values.current),
        setRange
    });
}
