import type { MetadataBounds } from '$lib/services/types';

type MetadataBound = MetadataBounds[string];

// bits-ui snaps a slider value onto the `step` grid and writes the result back into the state it
// watches. For a high-precision float step it rounds the value to the precision of step.toString(),
// which makes the snap non-idempotent: the value drifts ~1 ULP each pass and never settles, so the
// effect loops forever (effect_update_depth_exceeded). An integer tick domain (step 1) is always
// on-grid, so the snap is a no-op and the loop can't start. Real values are used only for display
// and commit.
export const FLOAT_SLIDER_TICKS = 1000; // float granularity: 0.1% of the range

/**
 * Number of slider ticks (integer domain 0..ticks, step 1) for a field.
 * Integer fields get one tick per integer so every value stays selectable even for wide ranges.
 * Float fields use a fixed resolution since their real values aren't enumerable anyway.
 */
export const getSliderTickCount = (bound: MetadataBound, isInteger: boolean): number => {
    return isInteger ? Math.max(1, bound.max - bound.min) : FLOAT_SLIDER_TICKS;
};

/** Map a real metadata value onto the slider's integer tick domain, clamped to [0, ticks]. */
export const toTick = (realValue: number, bound: MetadataBound, ticks: number): number => {
    if (bound.max === bound.min) {
        return 0;
    }
    const tick = Math.round(((realValue - bound.min) / (bound.max - bound.min)) * ticks);
    return Math.min(ticks, Math.max(0, tick));
};

/** Map a slider tick back to a real metadata value; endpoints return the exact bounds. */
export const fromTick = (
    tick: number,
    bound: MetadataBound,
    ticks: number,
    isInteger: boolean
): number => {
    if (tick <= 0) {
        return bound.min;
    }
    if (tick >= ticks) {
        return bound.max;
    }
    const realValue = bound.min + (tick / ticks) * (bound.max - bound.min);
    return isInteger ? Math.round(realValue) : realValue;
};
