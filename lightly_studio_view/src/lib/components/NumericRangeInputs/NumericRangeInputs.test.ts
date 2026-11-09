import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'svelte';
import { NumericRangeInputs } from '.';

const defaultProps = {
    label: 'Width',
    bound: { min: 0, max: 1000 },
    value: { min: 257, max: 800 },
    integer: true,
    unit: 'px'
};
const setup = (props: Partial<ComponentProps<typeof NumericRangeInputs>> = {}) => {
    const onValueCommit = vi.fn();
    const view = render(NumericRangeInputs, { ...defaultProps, ...props, onValueCommit });
    return { ...view, onValueCommit, min: screen.getByRole('textbox', { name: 'Width minimum' }) };
};

describe('NumericRangeInputs', () => {
    it('commits on Enter once, without committing while typing or on subsequent blur', async () => {
        const { min, onValueCommit } = setup();
        expect(onValueCommit).not.toHaveBeenCalled();
        await fireEvent.input(min, { target: { value: '250' } });
        expect(await fireEvent.keyDown(min, { key: 'Enter', isComposing: true })).toBe(true);
        expect(onValueCommit).not.toHaveBeenCalled();
        await fireEvent.keyDown(min, { key: 'Enter' });
        await fireEvent.blur(min);
        expect(onValueCommit).toHaveBeenCalledExactlyOnceWith([250, 800]);
    });

    it.each(['', 'Infinity', 'abc', '-1', '1001', '801', '250.5'])(
        'rejects invalid minimum %s and allows correction',
        async (value) => {
            const { min, onValueCommit } = setup();
            await fireEvent.input(min, { target: { value } });
            await fireEvent.blur(min);
            expect(min).toHaveAttribute('aria-invalid', 'true');
            expect(screen.getByRole('alert')).toBeInTheDocument();
            expect(onValueCommit).not.toHaveBeenCalled();
            await fireEvent.input(min, { target: { value: '800' } });
            await fireEvent.blur(min);
            expect(onValueCommit).toHaveBeenCalledExactlyOnceWith([800, 800]);
        }
    );

    it('preserves exact decimals and the opposite endpoint', async () => {
        const { onValueCommit } = setup({ integer: false });
        const max = screen.getByRole('textbox', { name: 'Width maximum' });
        await fireEvent.input(max, { target: { value: '799.123456789' } });
        await fireEvent.blur(max);
        expect(onValueCommit).toHaveBeenCalledExactlyOnceWith([257, 799.123456789]);
    });

    it('rejects a maximum below the minimum and ignores unchanged values', async () => {
        const { min, onValueCommit } = setup();
        const max = screen.getByRole('textbox', { name: 'Width maximum' });
        await fireEvent.input(max, { target: { value: '256' } });
        await fireEvent.blur(max);
        expect(max).toHaveAttribute('aria-invalid', 'true');
        await fireEvent.input(min, { target: { value: '257' } });
        await fireEvent.keyDown(min, { key: 'Tab' });
        await fireEvent.blur(min);
        expect(onValueCommit).not.toHaveBeenCalled();
    });

    it('preserves other drafts on commit but clears them on Escape or external reset', async () => {
        const { min, onValueCommit, rerender } = setup();
        await fireEvent.input(min, { target: { value: '250' } });
        await fireEvent.keyDown(min, { key: 'Escape' });
        await fireEvent.blur(min);
        expect(min).toHaveValue('257');
        await fireEvent.input(min, { target: { value: 'invalid' } });
        await fireEvent.blur(min);
        const max = screen.getByRole('textbox', { name: 'Width maximum' });
        await fireEvent.input(max, { target: { value: '900' } });
        await fireEvent.blur(max);
        expect(onValueCommit).toHaveBeenCalledExactlyOnceWith([257, 900]);
        await rerender({ ...defaultProps, value: { min: 257, max: 900 }, onValueCommit });
        expect(min).toHaveValue('invalid');
        expect(min).toHaveAttribute('aria-invalid', 'true');
        onValueCommit.mockClear();
        await rerender({ ...defaultProps, value: { min: 0, max: 1000 }, onValueCommit });
        expect(min).toHaveValue('0');
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(onValueCommit).not.toHaveBeenCalled();
    });
});
