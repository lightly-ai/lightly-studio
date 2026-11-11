import { afterEach, expect, it } from 'vitest';
import { flushSync } from 'svelte';
import { get } from 'svelte/store';
import { useDimensions } from '$lib/hooks';
import { useDimensionFilterChips } from './useDimensionFilterChips.svelte';

let cleanup: (() => void) | undefined;
afterEach(() => cleanup?.());

it('provides width and height chips and resets one to its bounds', () => {
    const { dimensionsValues, updateDimensionsBounds, updateDimensionsValues } = useDimensions();
    const full = { min_width: 10, max_width: 100, min_height: 20, max_height: 200 };
    updateDimensionsBounds(full);
    updateDimensionsValues({ ...full, min_width: 50, max_height: 150 });
    let hook!: ReturnType<typeof useDimensionFilterChips>;
    cleanup = $effect.root(() => {
        hook = useDimensionFilterChips();
    });
    flushSync();

    expect(hook.chips).toEqual([
        { key: 'width', active: true, range: { min: 50, max: 100 } },
        { key: 'height', active: true, range: { min: 20, max: 150 } }
    ]);

    hook.handleClear('width');

    expect(get(dimensionsValues)).toEqual({ ...full, max_height: 150 });
});
