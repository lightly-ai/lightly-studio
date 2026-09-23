import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import NamePickerField from './NamePickerField.svelte';

const defaultProps = {
    label: 'Annotation class',
    placeholder: 'Select an annotation class',
    names: ['dog', 'cat'],
    onSelect: vi.fn()
};

describe('NamePickerField', () => {
    it('reports a keyboard selection once', async () => {
        const onSelect = vi.fn();
        render(NamePickerField, { props: { ...defaultProps, onSelect } });

        await fireEvent.click(screen.getByTestId('select-list-trigger'));
        const input = screen.getByTestId('select-list-input');
        await fireEvent.input(input, { target: { value: 'dog' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(onSelect).toHaveBeenCalledExactlyOnceWith('dog');
    });
});
