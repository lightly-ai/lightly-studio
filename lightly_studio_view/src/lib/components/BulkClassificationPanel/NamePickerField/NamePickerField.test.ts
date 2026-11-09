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

    const search = async (value: string) => {
        await fireEvent.click(screen.getByTestId('select-list-trigger'));
        await fireEvent.input(screen.getByTestId('select-list-input'), { target: { value } });
    };

    it('keeps the default not-found behavior when creation is allowed', async () => {
        render(NamePickerField, { props: defaultProps });

        await search('zebra');

        expect(screen.queryByText('No annotation class found.')).not.toBeInTheDocument();
        expect(screen.queryByText(/Press Enter to create|Type to create/)).not.toBeInTheDocument();
    });

    it('shows "No annotation class found." and no create row when creation is not allowed', async () => {
        render(NamePickerField, { props: { ...defaultProps, allowCreate: false } });

        await search('zebra');

        expect(screen.getByText('No annotation class found.')).toBeInTheDocument();
        expect(screen.queryByText(/Create:/)).not.toBeInTheDocument();
    });
});
