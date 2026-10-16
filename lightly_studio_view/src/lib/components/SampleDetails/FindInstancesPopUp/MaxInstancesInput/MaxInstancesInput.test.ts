import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MaxInstancesInput from './MaxInstancesInput.svelte';

describe('MaxInstancesInput', () => {
    it('clamps the value to the instance limit and to at least one', async () => {
        const onChange = vi.fn();
        render(MaxInstancesInput, { props: { value: 16, onChange } });
        const input = screen.getByLabelText('Maximum instances');

        await fireEvent.change(input, { target: { value: '100' } });
        expect(onChange).toHaveBeenLastCalledWith(32);
        expect(input).toHaveValue(32);

        await fireEvent.change(input, { target: { value: '0' } });
        expect(onChange).toHaveBeenLastCalledWith(1);
    });
});
