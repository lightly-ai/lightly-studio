import { afterEach, describe, expect, test } from 'vitest';
import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors/useCustomSourceColors';
import { getColorBySource } from './getColorBySource';
import { getDefaultColor } from './getColorByLabel';

describe('getColorBySource', () => {
    afterEach(() => {
        useCustomSourceColors().clearCustomColors();
    });

    test('uses a custom source color', () => {
        useCustomSourceColors().setCustomColor('Predictions', '#ff0000', 0.5);

        expect(getColorBySource('Predictions', 0.5).color).toBe('rgba(255, 0, 0, 0.25)');
    });

    test('falls back to getDefaultColor', () => {
        expect(getColorBySource('Predictions', 0.7)).toEqual(getDefaultColor('Predictions', 0.7));
    });
});
