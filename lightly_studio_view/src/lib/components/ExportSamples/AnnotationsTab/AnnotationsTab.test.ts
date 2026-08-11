import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AnnotationsTab from './AnnotationsTab.svelte';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

const mocks = vi.hoisted(() => ({
    exportCollectionAnnotationsPrepare: vi.fn()
}));
vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionAnnotationsPrepare: mocks.exportCollectionAnnotationsPrepare,
    SortDirection: { ASC: 'ASC', DESC: 'DESC' }
}));

const imageFilterStore = writable(null);
vi.mock('$lib/hooks', () => ({
    useImageFilters: () => ({ imageFilter: imageFilterStore })
}));

vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: vi.fn()
}));

const defaultProps = {
    exportFormat: 'object_detection_coco' as const,
    description: 'Export in COCO format',
    annotationSources: [{ id: 'source-1', name: 'Source 1' }],
    selectedAnnotationCollectionId: undefined,
    testId: 'submit-button-annotations',
    sampleType: 'image' as const
};

describe('AnnotationsTab', () => {
    beforeEach(() => {
        mocks.exportCollectionAnnotationsPrepare.mockReset();
        vi.mocked(useVideoFilters).mockReturnValue({
            videoFilter: writable(null),
            filterParams: writable(null),
            updateFilterParams: vi.fn(),
            updateSampleIds: vi.fn()
        });
    });

    it('renders the description text', () => {
        render(AnnotationsTab, { props: defaultProps });
        expect(screen.getByText('Export in COCO format')).toBeInTheDocument();
    });

    it('hides the annotation source select for one source and shows it for multiple sources', () => {
        const { unmount } = render(AnnotationsTab, { props: defaultProps });
        expect(screen.queryByText('Annotation Source')).not.toBeInTheDocument();
        unmount();

        render(AnnotationsTab, {
            props: {
                ...defaultProps,
                annotationSources: [
                    { id: 'source-1', name: 'Source 1' },
                    { id: 'source-2', name: 'Source 2' }
                ]
            }
        });
        expect(screen.getByText('Annotation Source')).toBeInTheDocument();
    });

    it('calls the API using the first annotation source when none is selected', async () => {
        vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionAnnotationsPrepare.mockResolvedValue({
            data: { export_key: 'key123' }
        });
        render(AnnotationsTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('submit-button-annotations'));
        await waitFor(() => {
            expect(mocks.exportCollectionAnnotationsPrepare).toHaveBeenCalledWith({
                path: { collection_id: 'test-collection' },
                body: {
                    export_format: 'object_detection_coco',
                    annotation_collection_id: 'source-1',
                    image_filter: null
                }
            });
        });
    });

    it('opens a new tab with the download URL on success', async () => {
        const openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionAnnotationsPrepare.mockResolvedValue({
            data: { export_key: 'key123' }
        });
        render(AnnotationsTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('submit-button-annotations'));
        await waitFor(() => {
            expect(openSpy).toHaveBeenCalledWith(
                expect.stringContaining('/export/download/key123'),
                '_blank'
            );
        });
    });

    it('passes the active video filter and annotation source for video classifications', async () => {
        vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionAnnotationsPrepare.mockResolvedValue({
            data: { export_key: 'key123' }
        });
        const activeFilter = { filter_type: 'video' as const, width: { min: 100 } };
        vi.mocked(useVideoFilters).mockReturnValueOnce({
            videoFilter: writable(activeFilter),
            filterParams: writable(null),
            updateFilterParams: vi.fn(),
            updateSampleIds: vi.fn()
        });
        render(AnnotationsTab, {
            props: {
                ...defaultProps,
                exportFormat: 'classification_csv',
                selectedAnnotationCollectionId: 'source-2',
                sampleType: 'video'
            }
        });

        await fireEvent.click(screen.getByTestId('submit-button-annotations'));

        expect(mocks.exportCollectionAnnotationsPrepare).toHaveBeenCalledWith({
            path: { collection_id: 'test-collection' },
            body: {
                export_format: 'classification_csv',
                annotation_collection_id: 'source-2',
                video_filter: activeFilter
            }
        });
    });

    it('shows an error message when the API fails', async () => {
        mocks.exportCollectionAnnotationsPrepare.mockRejectedValue(new Error('Network error'));
        render(AnnotationsTab, { props: defaultProps });
        await fireEvent.click(screen.getByTestId('submit-button-annotations'));
        await waitFor(() => {
            expect(screen.getByText(/Export failed/)).toBeInTheDocument();
        });
    });

    it('calls onDownloadClick when the download button is clicked', async () => {
        vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionAnnotationsPrepare.mockResolvedValue({
            data: { export_key: 'key123' }
        });
        const onDownloadClick = vi.fn();
        render(AnnotationsTab, { props: { ...defaultProps, onDownloadClick } });
        await fireEvent.click(screen.getByTestId('submit-button-annotations'));
        expect(onDownloadClick).toHaveBeenCalledOnce();
    });
});
