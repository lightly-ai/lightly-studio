import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MaxInstancesInput from './MaxInstancesInput.svelte';

describe('MaxInstancesInput', () => {
    it('clamps the value to the instance limit and to at least one', async () => {
        const onChange = vi.fn();
        render(MaxInstancesInput, { props: { value: 16, onChange } });
        const input = screen.getByLabelText('Maximum instances');

        await fireEvent.input(input, { target: { value: '100' } });
        await fireEvent.change(input);
        expect(onChange).toHaveBeenLastCalledWith(32);
        expect(input).toHaveValue(32);

        await fireEvent.input(input, { target: { value: '0' } });
        await fireEvent.change(input);
        expect(onChange).toHaveBeenLastCalledWith(1);
    });

    it('keeps the previous value when the field is cleared', async () => {
        const onChange = vi.fn();
        render(MaxInstancesInput, { props: { value: 8, onChange } });
        const input = screen.getByLabelText('Maximum instances');

        await fireEvent.input(input, { target: { value: '' } });
        await fireEvent.change(input);
        expect(onChange).toHaveBeenLastCalledWith(8);
        expect(input).toHaveValue(8);
    });
});
