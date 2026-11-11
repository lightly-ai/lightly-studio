import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'svelte';
import { NumericRangeInputs } from '.';

const defaultProps = {
    label: 'Width',
    bound: { min: 0, max: 1000 },
    value: { min: 257, max: 800 },
    integer: true
};
const edit = async (input: HTMLElement, value: string, key?: string) => {
    await fireEvent.input(input, { target: { value } });
    await (key ? fireEvent.keyDown(input, { key }) : fireEvent.blur(input));
};
const input = (endpoint: string) => screen.getByRole('textbox', { name: `Width ${endpoint}` });
const setup = (props: Partial<ComponentProps<typeof NumericRangeInputs>> = {}) => {
    const onValueCommit = vi.fn();
    const view = render(NumericRangeInputs, { ...defaultProps, ...props, onValueCommit });
    const acknowledge = (min: number, max: number) => view.rerender({ value: { min, max } });
    return { acknowledge, onValueCommit, min: input('minimum') };
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

    it.each(['', '275'])('keeps draft %s on delayed acknowledgement', async (draft) => {
        const { min, acknowledge } = setup();
        await edit(min, '250', 'Enter');
        await fireEvent.keyDown(min, { key: 'Escape' });
        if (draft) await fireEvent.input(min, { target: { value: draft } });
        await acknowledge(250, 800);
        expect(min).toHaveValue(draft || '250');
    });

    it.each(['', 'Infinity', 'abc', '-1', '1001', '801', '250.5'])(
        'rejects %s and accepts correction',
        async (value) => {
            const { min, onValueCommit } = setup();
            await edit(min, value);
            expect(min).toHaveAttribute('aria-invalid', 'true');
            expect(screen.getByRole('alert')).toBeInTheDocument();
            expect(onValueCommit).not.toHaveBeenCalled();
            await edit(min, '800');
            expect(onValueCommit).toHaveBeenCalledExactlyOnceWith([800, 800]);
        }
    );

    it.each([
        { endpoint: 'minimum', draft: '0.7', corrected: '0.8', expected: [0.7, 0.8] },
        { endpoint: 'maximum', draft: '0.1', corrected: '0.05', expected: [0.05, 0.1] }
    ])(
        'applies the rejected $endpoint draft when the other bound makes it valid',
        async ({ endpoint, draft, corrected, expected }) => {
            const { onValueCommit, acknowledge } = setup({
                integer: false,
                bound: { min: 0, max: 1 },
                value: { min: 0.2, max: 0.5 }
            });
            const invalid = input(endpoint);
            const other = input(endpoint === 'minimum' ? 'maximum' : 'minimum');
            await edit(invalid, draft);
            expect(invalid).toHaveAttribute('aria-invalid', 'true');
            await edit(other, corrected);
            expect(invalid).toHaveAttribute('aria-invalid', 'false');
            expect(screen.queryByRole('alert')).not.toBeInTheDocument();
            expect(onValueCommit).toHaveBeenCalledExactlyOnceWith(expected);
            await acknowledge(expected[0], expected[1]);
            expect(invalid).toHaveValue(draft);
            expect(screen.queryByRole('alert')).not.toBeInTheDocument();
            await fireEvent.blur(invalid);
            await fireEvent.keyDown(invalid, { key: 'Enter' });
            expect(onValueCommit).toHaveBeenCalledExactlyOnceWith(expected);
        }
    );

    it('composes exact pending edits before acknowledgement', async () => {
        const { min, onValueCommit } = setup({ integer: false, unit: 'px' });
        await edit(min, '200.123');
        await edit(input('maximum'), '225.123456789');
        expect(onValueCommit).toHaveBeenLastCalledWith([200.123, 225.123456789]);
    });

    it('rejects a maximum below the minimum and ignores unchanged values', async () => {
        const { min, onValueCommit } = setup();
        await edit(input('maximum'), '256');
        expect(input('maximum')).toHaveAttribute('aria-invalid', 'true');
        await edit(min, '257', 'Tab');
        await fireEvent.blur(min);
        expect(onValueCommit).not.toHaveBeenCalled();
    });

    it('preserves other drafts on commit but clears them on Escape or external reset', async () => {
        const { min, onValueCommit, acknowledge } = setup();
        await edit(min, '250', 'Escape');
        await fireEvent.blur(min);
        expect(min).toHaveValue('257');
        await edit(min, 'invalid');
        await edit(input('maximum'), '900');
        expect(onValueCommit).toHaveBeenCalledExactlyOnceWith([257, 900]);
        await acknowledge(257, 900);
        expect(min).toHaveValue('invalid');
        expect(min).toHaveAttribute('aria-invalid', 'true');
        await edit(input('maximum'), '950');
        await acknowledge(0, 1000);
        expect(min).toHaveValue('0');
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(onValueCommit).toHaveBeenCalledTimes(2);
    });
});
