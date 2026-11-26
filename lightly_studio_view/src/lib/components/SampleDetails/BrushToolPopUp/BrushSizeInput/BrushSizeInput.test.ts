import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import BrushSizeInput from './BrushSizeInput.svelte';

describe('BrushSizeInput', () => {
    it('shows the size in px and the slider at its log position', () => {
        render(BrushSizeInput, { props: { size: 37, onChange: vi.fn() } });

        expect(screen.getByLabelText('Brush size in pixels')).toHaveValue(37);
        expect(screen.getByText('px')).toBeInTheDocument();
        expect(screen.getByRole('slider', { name: 'Brush size' })).toHaveValue('581');
    });

    it('applies a typed size on Enter', async () => {
        const onChange = vi.fn();
        render(BrushSizeInput, { props: { size: 100, onChange } });
        const field = screen.getByLabelText('Brush size in pixels');

        await fireEvent.input(field, { target: { value: '37' } });
        expect(onChange).not.toHaveBeenCalled();
        await fireEvent.keyDown(field, { key: 'Enter' });

        expect(onChange).toHaveBeenCalledWith(37);
    });

    it('applies a typed size on blur', async () => {
        const onChange = vi.fn();
        render(BrushSizeInput, { props: { size: 100, onChange } });
        const field = screen.getByLabelText('Brush size in pixels');

        await fireEvent.input(field, { target: { value: '1' } });
        await fireEvent.blur(field);

        expect(onChange).toHaveBeenCalledWith(1);
    });

    it('clamps a typed size above 500 px', async () => {
        const onChange = vi.fn();
        render(BrushSizeInput, { props: { size: 100, onChange } });
        const field = screen.getByLabelText('Brush size in pixels');

        await fireEvent.input(field, { target: { value: '900' } });
        await fireEvent.keyDown(field, { key: 'Enter' });

        expect(onChange).toHaveBeenCalledWith(500);
        expect(field).toHaveValue(500);
    });

    it('goes back to the last size for empty input', async () => {
        const onChange = vi.fn();
        render(BrushSizeInput, { props: { size: 100, onChange } });
        const field = screen.getByLabelText('Brush size in pixels');

        await fireEvent.input(field, { target: { value: '' } });
        await fireEvent.blur(field);

        expect(onChange).not.toHaveBeenCalled();
        expect(field).toHaveValue(100);
    });

    it('steps by 1 with the arrow keys and by 10 with Shift', async () => {
        const onChange = vi.fn();
        render(BrushSizeInput, { props: { size: 100, onChange } });
        const field = screen.getByLabelText('Brush size in pixels');

        await fireEvent.keyDown(field, { key: 'ArrowUp' });
        expect(onChange).toHaveBeenLastCalledWith(101);

        await fireEvent.keyDown(field, { key: 'ArrowDown', shiftKey: true });
        expect(onChange).toHaveBeenLastCalledWith(90);
    });

    it('keeps arrow steps within 1 to 500 px', async () => {
        const onChange = vi.fn();
        render(BrushSizeInput, { props: { size: 1, onChange } });
        const field = screen.getByLabelText('Brush size in pixels');

        await fireEvent.keyDown(field, { key: 'ArrowDown', shiftKey: true });

        expect(onChange).toHaveBeenLastCalledWith(1);
    });

    it('applies the slider position on the log scale', async () => {
        const onChange = vi.fn();
        render(BrushSizeInput, { props: { size: 100, onChange } });

        await fireEvent.input(screen.getByRole('slider', { name: 'Brush size' }), {
            target: { value: '1000' }
        });

        expect(onChange).toHaveBeenCalledWith(500);
    });

    it('shows a new size from outside', async () => {
        const { rerender } = render(BrushSizeInput, { props: { size: 100, onChange: vi.fn() } });

        await rerender({ size: 110, onChange: vi.fn() });

        expect(screen.getByLabelText('Brush size in pixels')).toHaveValue(110);
    });
});
