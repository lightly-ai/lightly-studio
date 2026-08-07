import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable } from 'svelte/store';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import SamplesTab from './SamplesTab.svelte';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionPrepare: vi.fn(),
    SortDirection: { ASC: 'ASC', DESC: 'DESC' }
}));

let tagsStore: ReturnType<typeof writable<{ tag_id: string; name: string; kind: string }[]>>;
vi.mock('$lib/hooks', () => ({
    useTags: () => ({ tags: tagsStore }),
    useImageFilters: () => ({ imageFilter: writable(null) })
}));

vi.mock('../useExportSamplesCount/useExportSamplesCount.svelte', () => ({
    useExportSamplesCount: () => ({
        count: writable(0),
        isLoading: writable(false),
        error: writable(undefined)
    })
}));

vi.mock('../useExportDownload/useExportDownload', () => ({
    useExportDownload: () => ({
        isLoading: writable(false),
        errorMessage: writable(undefined),
        handleDownload: vi.fn()
    })
}));

// Bits-UI Select uses pointer-capture APIs not present in jsdom
const originalHasPointerCapture = Element.prototype.hasPointerCapture;
const originalSetPointerCapture = Element.prototype.setPointerCapture;
const originalReleasePointerCapture = Element.prototype.releasePointerCapture;

beforeAll(() => {
    Element.prototype.hasPointerCapture = vi.fn(() => false);
    Element.prototype.setPointerCapture = vi.fn();
    Element.prototype.releasePointerCapture = vi.fn();
});

afterAll(() => {
    Element.prototype.hasPointerCapture = originalHasPointerCapture;
    Element.prototype.setPointerCapture = originalSetPointerCapture;
    Element.prototype.releasePointerCapture = originalReleasePointerCapture;
});

describe('SamplesTab', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        tagsStore = writable([]);
    });

    it('renders initial state with placeholder, checkbox, disabled button, and helper text', () => {
        render(SamplesTab);
        expect(
            screen.getByText('Select a tag to export its samples (required)')
        ).toBeInTheDocument();
        expect(screen.getByText('Inverse selection')).toBeInTheDocument();
        expect(screen.getByTestId('submit-button-samples')).toBeDisabled();
        expect(
            screen.getByText(/Inverse selection will export all samples that are not selected/)
        ).toBeInTheDocument();
    });

    it('calls onDownloadClick when the download button is clicked', async () => {
        tagsStore = writable([{ tag_id: 'tag-1', name: 'My Tag', kind: 'sample' }]);
        const onDownloadClick = vi.fn();
        render(SamplesTab, { props: { onDownloadClick } });

        const user = userEvent.setup();
        await user.click(screen.getByText('Select a tag to export its samples (required)'));
        const option = await waitFor(() => screen.getByRole('option', { name: 'My Tag' }));
        await user.click(option);
        await waitFor(() => expect(screen.getByTestId('submit-button-samples')).not.toBeDisabled());
        await fireEvent.click(screen.getByTestId('submit-button-samples'));

        expect(onDownloadClick).toHaveBeenCalledOnce();
    });
});
