import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ExportDownloadButton from './ExportDownloadButton.svelte';

const defaultProps = {
    isLoading: false,
    errorMessage: '',
    onclick: vi.fn(),
    testId: 'download-button'
};

describe('ExportDownloadButton', () => {
    beforeEach(vi.resetAllMocks);

    it('renders and calls onclick when the button is clicked', async () => {
        const onclick = vi.fn();
        render(ExportDownloadButton, { props: { ...defaultProps, onclick } });
        const button = screen.getByTestId('download-button');
        expect(button).toBeInTheDocument();
        await fireEvent.click(button);
        expect(onclick).toHaveBeenCalledOnce();
    });

    it('disables the button and shows a spinner when isLoading is true', () => {
        render(ExportDownloadButton, { props: { ...defaultProps, isLoading: true } });
        expect(screen.getByTestId('download-button')).toBeDisabled();
        expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('disables the button when the disabled prop is true', () => {
        render(ExportDownloadButton, { props: { ...defaultProps, disabled: true } });
        expect(screen.getByTestId('download-button')).toBeDisabled();
    });

    it('shows the error message when errorMessage is set', () => {
        render(ExportDownloadButton, {
            props: { ...defaultProps, errorMessage: 'Export failed: some error' }
        });
        expect(screen.getByText('Export failed: some error')).toBeInTheDocument();
    });
});
