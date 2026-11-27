import { MAX_BRUSH_SIZE, MIN_BRUSH_SIZE } from '$lib/contexts/SampleDetailsToolbar.svelte';

export const SLIDER_STEPS = 1000;
const WHEEL_STEP_RATIO = 0.1;
const WHOLE_NUMBER = /^-?\d+$/;

export const clampBrushSize = (size: number): number =>
    Math.min(MAX_BRUSH_SIZE, Math.max(MIN_BRUSH_SIZE, Math.round(size)));

// The slider is logarithmic, so small sizes take most of its travel.
export const sliderPositionToBrushSize = (position: number): number =>
    clampBrushSize(MAX_BRUSH_SIZE ** (position / SLIDER_STEPS));

export const brushSizeToSliderPosition = (size: number): number =>
    Math.round((SLIDER_STEPS * Math.log(size)) / Math.log(MAX_BRUSH_SIZE));

export const getWheelStep = (size: number): number =>
    Math.max(1, Math.round(size * WHEEL_STEP_RATIO));

export const parseBrushSize = (text: string): number | undefined => {
    const trimmed = text.trim();
    if (!WHOLE_NUMBER.test(trimmed)) return undefined;
    return clampBrushSize(Number(trimmed));
};
