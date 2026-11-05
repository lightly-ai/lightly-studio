import { render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors';
import ColorDot from './ColorDot.svelte';

const RED = '#ff0000';
const BLUE = '#0000ff';

const dotColor = () => screen.getByTestId('dot').style.backgroundColor;

describe('ColorDot', () => {
    afterEach(() => {
        useCustomLabelColors().clearCustomColors();
        useCustomSourceColors().clearCustomColors();
    });

    it('shows the custom class color of a class', () => {
        useCustomLabelColors().setCustomColor('gt', BLUE);

        render(ColorDot, { props: { label: 'gt', testId: 'dot' } });

        expect(dotColor()).toBe('rgb(0, 0, 255)');
    });

    it('shows the custom source color of a source, not the color of a class with its name', () => {
        useCustomSourceColors().setCustomColor('gt', RED);
        useCustomLabelColors().setCustomColor('gt', BLUE);

        render(ColorDot, { props: { label: 'gt', kind: 'source', testId: 'dot' } });

        expect(dotColor()).toBe('rgb(255, 0, 0)');
    });
});
