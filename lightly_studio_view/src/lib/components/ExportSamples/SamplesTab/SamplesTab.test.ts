import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SamplesTab from './SamplesTab.svelte';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionPrepare: vi.fn(),
    SortDirection: { ASC: 'ASC', DESC: 'DESC' }
}));

vi.mock('$lib/hooks', () => ({
    useImageFilters: () => ({ imageFilter: writable(null) })
}));

vi.mock('../useExportDownload/useExportDownload', () => ({
    useExportDownload: () => ({
        isLoading: writable(false),
        errorMessage: writable(undefined),
        handleDownload: vi.fn()
    })
}));

describe('SamplesTab', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('renders with an enabled download button and no tag selector or inverse checkbox', () => {
        render(SamplesTab);
        expect(screen.getByTestId('submit-button-samples')).not.toBeDisabled();
        expect(screen.queryByText('Inverse selection')).not.toBeInTheDocument();
        expect(
            screen.queryByText('Select a tag to export its samples (required)')
        ).not.toBeInTheDocument();
    });

    it('calls onDownloadClick when the download button is clicked', async () => {
        const onDownloadClick = vi.fn();
        render(SamplesTab, { props: { onDownloadClick } });

        await fireEvent.click(screen.getByTestId('submit-button-samples'));

        expect(onDownloadClick).toHaveBeenCalledOnce();
    });
});
