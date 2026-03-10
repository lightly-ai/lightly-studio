const METADATA_SLIDER_TICKS = 1000;
const GRID_EPSILON = 1e-9;

export const getMetadataSliderStep = (min: number, max: number, isInteger: boolean): number => {
    const step = (max - min) / METADATA_SLIDER_TICKS;
    if (step <= 0) {
        return isInteger ? 1 : 1 / METADATA_SLIDER_TICKS;
    }
    if (isInteger) {
        return Math.max(1, Math.round(step));
    }
    return step;
};

export const getMetadataSliderMax = (min: number, max: number, step: number): number => {
    const steps = (max - min) / step;
    const isMaxOnStepGrid = Math.abs(steps - Math.round(steps)) < GRID_EPSILON;
    return isMaxOnStepGrid ? max : max + step;
};

export const getSliderDisplayMaxValue = (
    valueMax: number,
    boundMax: number,
    sliderMax: number
): number => {
    return valueMax >= boundMax ? sliderMax : valueMax;
};

export const clampMetadataValuesToMax = (
    newValues: number[],
    boundMax: number
): [number, number] => {
    return [Math.min(newValues[0], boundMax), Math.min(newValues[1], boundMax)];
};
