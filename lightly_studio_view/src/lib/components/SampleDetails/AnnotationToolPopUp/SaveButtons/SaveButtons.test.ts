import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import SaveButtons from './SaveButtons.svelte';

const defaultProps = {
    canSave: true,
    onSave: vi.fn(),
    onClear: vi.fn()
};

describe('SaveButtons', () => {
    it('disables Done when canSave is false', () => {
        render(SaveButtons, { props: { ...defaultProps, canSave: false } });
        expect(screen.getByRole('button', { name: 'Done' })).toBeDisabled();
    });

    it('shows saving progress and blocks Done and Reset while saving', () => {
        render(SaveButtons, { props: { ...defaultProps, isSaving: true } });
        expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Reset' })).toBeDisabled();
    });

    it('shows the save label', () => {
        render(SaveButtons, { props: { ...defaultProps, saveLabel: 'Save 3' } });
        expect(screen.getByRole('button', { name: 'Save 3' })).toBeInTheDocument();
    });

    it('calls onSave and onClear', async () => {
        const onSave = vi.fn();
        const onClear = vi.fn();
        render(SaveButtons, { props: { ...defaultProps, onSave, onClear } });
        await fireEvent.click(screen.getByRole('button', { name: 'Done' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Reset' }));
        expect(onSave).toHaveBeenCalledOnce();
        expect(onClear).toHaveBeenCalledOnce();
    });
});
