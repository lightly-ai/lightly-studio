import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ColorPickerPanel from './color-picker-panel.svelte';

const hsl = { h: 10, s: 100, l: 50 };
const defaultProps = {
    hsl,
    hex: '#ff2a00',
    alpha: 1,
    onHslChange: vi.fn(),
    onHexChange: vi.fn(),
    onAlphaChange: vi.fn(),
    onApply: vi.fn(),
    onCancel: vi.fn()
};

describe('ColorPickerPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('changes the hue with the keyboard', async () => {
        render(ColorPickerPanel, { props: defaultProps });

        const slider = screen.getByRole('slider', { name: 'Hue' });
        slider.focus();
        await fireEvent.keyDown(slider, { key: 'ArrowRight' });

        expect(defaultProps.onHslChange).toHaveBeenCalledWith({ ...hsl, h: 11 });
    });

    it('accepts uppercase hex and ignores partial hex', async () => {
        render(ColorPickerPanel, { props: defaultProps });
        const input = screen.getByLabelText('Hex color');

        await fireEvent.input(input, { target: { value: '#12' } });
        expect(defaultProps.onHexChange).not.toHaveBeenCalled();

        await fireEvent.input(input, { target: { value: '#00FF00' } });
        expect(defaultProps.onHexChange).toHaveBeenCalledWith('#00ff00');
    });

    it('marks the selected preset', () => {
        render(ColorPickerPanel, { props: { ...defaultProps, hex: '#0000ff' } });

        expect(screen.getByRole('button', { name: '#0000ff' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
        expect(screen.getByRole('button', { name: '#ff0000' })).toHaveAttribute(
            'aria-pressed',
            'false'
        );
    });
});
