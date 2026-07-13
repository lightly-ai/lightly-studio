import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import ExportDownloadButton from './ExportDownloadButton.svelte';

describe('ExportDownloadButton', () => {
    it('renders the Download button with the given testId', () => {
        render(ExportDownloadButton, { props: { onclick: vi.fn(), testId: 'test-btn' } });

        expect(screen.getByTestId('test-btn')).toBeInTheDocument();
        expect(screen.getByTestId('test-btn')).toHaveTextContent('Download');
    });

    it('does not show loading spinner by default', () => {
        const { container } = render(ExportDownloadButton, {
            props: { onclick: vi.fn(), testId: 'test-btn' }
        });

        expect(container.querySelector('[data-testid="loading-spinner"]')).toBeNull();
    });

    it('shows loading spinner when isLoading is true', () => {
        const { container } = render(ExportDownloadButton, {
            props: { onclick: vi.fn(), testId: 'test-btn', isLoading: true }
        });

        expect(container.querySelector('[data-testid="loading-spinner"]')).toBeInTheDocument();
    });

    it('disables the button when disabled is true', () => {
        render(ExportDownloadButton, {
            props: { onclick: vi.fn(), testId: 'test-btn', disabled: true }
        });

        expect(screen.getByTestId('test-btn')).toBeDisabled();
    });

    it('calls onclick when clicked', async () => {
        const onclick = vi.fn();
        render(ExportDownloadButton, { props: { onclick, testId: 'test-btn' } });

        await fireEvent.click(screen.getByTestId('test-btn'));

        expect(onclick).toHaveBeenCalledOnce();
    });
});
