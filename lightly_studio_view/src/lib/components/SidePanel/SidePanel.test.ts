import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import SidePanel from './SidePanel.svelte';
import TestContent from './TestContent.svelte';
import type { Snippet } from 'svelte';

describe('SidePanel Component', () => {
    const defaultProps = {
        title: 'Test SidePanel',
        isOpen: true,
        children: TestContent as unknown as Snippet,
        onSubmit: vi.fn(),
        onOpenChange: vi.fn()
    };

    it('renders with basic props', () => {
        render(SidePanel, defaultProps);

        expect(screen.getByText('Test SidePanel')).toBeInTheDocument();
        expect(screen.getByText('Test Content')).toBeInTheDocument();
        expect(screen.getByText('Submit')).toBeInTheDocument();
        expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('renders custom button labels', () => {
        const submitLabel = 'Save';
        const cancelLabel = 'Close';
        render(SidePanel, {
            ...defaultProps,
            submitLabel,
            cancelLabel
        });

        expect(screen.getByTestId('submit-button')).toHaveTextContent(submitLabel);
        expect(screen.getByTestId('cancel-button')).toHaveTextContent(cancelLabel);
    });

    it('shows loading state', () => {
        render(SidePanel, {
            ...defaultProps,
            isLoading: true
        });

        expect(screen.getByTestId('submit-button')).toBeDisabled();
        expect(screen.getByTestId('cancel-button')).toBeDisabled();
        expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('shows error message', () => {
        render(SidePanel, {
            ...defaultProps,
            errorMessage: 'Test error message'
        });

        expect(screen.getByText('Test error message')).toBeInTheDocument();
        expect(screen.getByTestId('alert-destructive')).toBeInTheDocument();
    });

    it('shows success message', () => {
        render(SidePanel, {
            ...defaultProps,
            successMessage: 'Operation successful'
        });

        expect(screen.getByText('Operation successful')).toBeInTheDocument();
        expect(screen.getByTestId('alert-success')).toBeInTheDocument();
    });

    it('calls onSubmit when submit button is clicked', async () => {
        const mockOnSubmit = vi.fn();
        render(SidePanel, {
            ...defaultProps,
            onSubmit: mockOnSubmit
        });

        await fireEvent.click(screen.getByText('Submit'));
        expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    });

    it('calls onOpenChange when cancel button is clicked', async () => {
        const mockOnOpenChange = vi.fn();
        render(SidePanel, {
            ...defaultProps,
            onOpenChange: mockOnOpenChange
        });

        await fireEvent.click(screen.getByText('Cancel'));
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('disables submit button when disabled prop is true', () => {
        render(SidePanel, {
            ...defaultProps,
            isDisabled: true
        });

        expect(screen.getByTestId('submit-button')).toBeDisabled();
    });
});
