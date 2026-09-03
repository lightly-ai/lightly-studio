import type { MetadataBounds } from '$lib/services/types';

type MetadataBound = MetadataBounds[string];

// bits-ui snaps a slider value onto the `step` grid and writes the result back into the state it
// watches. For a high-precision float step it rounds the value to the precision of step.toString(),
// which makes the snap non-idempotent: the value drifts ~1 ULP each pass and never settles, so the
// effect loops forever (effect_update_depth_exceeded). An integer tick domain (step 1) is always
// on-grid, so the snap is a no-op and the loop can't start. Real values are used only for display
// and commit.
export const SLIDER_TICKS = 1000; // tick granularity: 0.1% of the range

/** Map a real metadata value onto the slider's integer tick domain, clamped to [0, SLIDER_TICKS]. */
export const toTick = (realValue: number, bound: MetadataBound): number => {
    if (bound.max === bound.min) {
        return 0;
    }
    const tick = Math.round(((realValue - bound.min) / (bound.max - bound.min)) * SLIDER_TICKS);
    return Math.min(SLIDER_TICKS, Math.max(0, tick));
};

/** Map a slider tick back to a real metadata value. */
export const fromTick = (tick: number, bound: MetadataBound, isInteger: boolean): number => {
    if (tick <= 0) {
        return bound.min;
    }
    if (tick >= SLIDER_TICKS) {
        return bound.max;
    }
    const realValue = bound.min + (tick / SLIDER_TICKS) * (bound.max - bound.min);
    return isInteger ? Math.round(realValue) : realValue;
};
