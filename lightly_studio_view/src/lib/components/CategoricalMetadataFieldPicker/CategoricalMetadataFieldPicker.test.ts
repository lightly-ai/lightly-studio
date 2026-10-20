import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import CategoricalMetadataFieldPicker from './CategoricalMetadataFieldPicker.svelte';

describe('CategoricalMetadataFieldPicker', () => {
    it('renders the trigger button', () => {
        render(CategoricalMetadataFieldPicker, {
            props: { fields: ['color', 'size'], onAdd: vi.fn() }
        });

        expect(
            screen.getByRole('button', { name: 'Add categorical metadata field' })
        ).toBeInTheDocument();
    });

    it('disables the trigger button when no fields are available', () => {
        render(CategoricalMetadataFieldPicker, {
            props: { fields: [], onAdd: vi.fn() }
        });

        expect(
            screen.getByRole('button', { name: 'Add categorical metadata field' })
        ).toBeDisabled();
    });

    it('enables the trigger button when fields are available', () => {
        render(CategoricalMetadataFieldPicker, {
            props: { fields: ['color'], onAdd: vi.fn() }
        });

        expect(
            screen.getByRole('button', { name: 'Add categorical metadata field' })
        ).not.toBeDisabled();
    });

    it('calls onAdd with the selected field when a field button is clicked', async () => {
        const onAdd = vi.fn();
        render(CategoricalMetadataFieldPicker, {
            props: { fields: ['color', 'size'], onAdd }
        });

        await fireEvent.click(
            screen.getByRole('button', { name: 'Add categorical metadata field' })
        );
        await fireEvent.click(screen.getByRole('button', { name: 'color' }));

        expect(onAdd).toHaveBeenCalledWith('color');
    });
});
