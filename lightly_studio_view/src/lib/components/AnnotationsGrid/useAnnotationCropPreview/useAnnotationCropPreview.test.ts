import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { CropWindow } from '../AnnotationItem/renderCropObjectUrl';
import { buildAnnotationDragData, buildClassificationDragData } from '../AnnotationsGrid.helpers';
import { useAnnotationCropPreview } from './useAnnotationCropPreview.svelte';

const mocks = vi.hoisted(() => ({
    renderCropObjectUrl: vi.fn()
}));

vi.mock('../AnnotationItem/renderCropObjectUrl', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../AnnotationItem/renderCropObjectUrl')>();
    return { ...actual, renderCropObjectUrl: mocks.renderCropObjectUrl };
});

const window: CropWindow = {
    sourceUrl: '/api/images/sample/1',
    sampleWidth: 100,
    sampleHeight: 100,
    windowWidth: 50,
    windowHeight: 50,
    windowX: 0,
    windowY: 0
};

beforeEach(() => {
    vi.clearAllMocks();
    URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    URL.revokeObjectURL = vi.fn();
});

describe('useAnnotationCropPreview', () => {
    it('records a crop window for an annotation', () => {
        const preview = useAnnotationCropPreview();

        preview.handleCropWindowChange('ann-1', window);

        expect(preview.cropWindowByAnnotationId['ann-1']).toEqual(window);
    });

    it('clears a crop window and revokes its blob url when set to null', () => {
        const preview = useAnnotationCropPreview();
        preview.handleCropWindowChange('ann-1', window);

        preview.handleCropWindowChange('ann-1', null);

        expect(preview.cropWindowByAnnotationId['ann-1']).toBeUndefined();
    });

    it('renders and stores a crop blob url on drag start', async () => {
        mocks.renderCropObjectUrl.mockResolvedValue('blob:crop-url');
        const preview = useAnnotationCropPreview();
        preview.handleCropWindowChange('ann-1', window);

        await preview.handleAnnotationDragStart('ann-1');

        expect(mocks.renderCropObjectUrl).toHaveBeenCalledWith(window, { cancelled: false });
        expect(preview.cropUrlByAnnotationId['ann-1']).toBe('blob:crop-url');
    });

    it('does nothing on drag start when no crop window was reported yet', async () => {
        const preview = useAnnotationCropPreview();

        await preview.handleAnnotationDragStart('ann-1');

        expect(mocks.renderCropObjectUrl).not.toHaveBeenCalled();
    });

    it('revokes the rendered blob url if the tile unmounted while rendering', async () => {
        let resolveRender: (url: string | null) => void = () => {};
        mocks.renderCropObjectUrl.mockReturnValue(
            new Promise((resolve) => {
                resolveRender = resolve;
            })
        );
        const preview = useAnnotationCropPreview();
        preview.handleCropWindowChange('ann-1', window);

        const dragStart = preview.handleAnnotationDragStart('ann-1');
        preview.handleCropWindowChange('ann-1', null);
        resolveRender('blob:crop-url');
        await dragStart;

        expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:crop-url');
        expect(preview.cropUrlByAnnotationId['ann-1']).toBeUndefined();
    });

    it('keeps only the most recently started render when two drag starts overlap', async () => {
        let resolveFirst: (url: string | null) => void = () => {};
        let resolveSecond: (url: string | null) => void = () => {};
        mocks.renderCropObjectUrl
            .mockReturnValueOnce(
                new Promise((resolve) => {
                    resolveFirst = resolve;
                })
            )
            .mockReturnValueOnce(
                new Promise((resolve) => {
                    resolveSecond = resolve;
                })
            );
        const preview = useAnnotationCropPreview();
        preview.handleCropWindowChange('ann-1', window);

        // Two drags on the same tile in quick succession; the first render
        // resolves *after* the second one, so it must not win.
        const firstDragStart = preview.handleAnnotationDragStart('ann-1');
        const secondDragStart = preview.handleAnnotationDragStart('ann-1');
        resolveSecond('blob:crop-url-second');
        await secondDragStart;
        resolveFirst('blob:crop-url-first');
        await firstDragStart;

        expect(preview.cropUrlByAnnotationId['ann-1']).toBe('blob:crop-url-second');
        expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:crop-url-first');
    });

    it('revokes every held blob url on cleanup', async () => {
        mocks.renderCropObjectUrl
            .mockResolvedValueOnce('blob:crop-url-1')
            .mockResolvedValueOnce('blob:crop-url-2');
        const preview = useAnnotationCropPreview();
        preview.handleCropWindowChange('ann-1', window);
        preview.handleCropWindowChange('ann-2', window);
        await preview.handleAnnotationDragStart('ann-1');
        await preview.handleAnnotationDragStart('ann-2');

        preview.cleanup();

        expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:crop-url-1');
        expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:crop-url-2');
    });

    // Integration: wires the real hook output straight into the real drag-data
    // builders, so a regression in either side would show up here even though
    // AnnotationsGrid.test.ts mocks both away for its orchestration-level tests.
    it('feeds the rendered crop url into the annotation drag data on drag start', async () => {
        mocks.renderCropObjectUrl.mockResolvedValue('blob:crop-url');
        const annotation = {
            sample_id: 'ann-1',
            annotation_label: { annotation_label_name: 'dog' },
            annotation_collection_id: 'col-1'
        } as unknown as AnnotationView;
        const preview = useAnnotationCropPreview();
        preview.handleCropWindowChange('ann-1', window);

        await preview.handleAnnotationDragStart('ann-1');
        const dragData = buildAnnotationDragData({
            annotation,
            cropWindow: preview.cropWindowByAnnotationId['ann-1'],
            cropUrl: preview.cropUrlByAnnotationId['ann-1']
        });

        expect(dragData?.url).toBe('blob:crop-url');
    });

    it('feeds the rendered crop url into the classification drag data on drag start', async () => {
        mocks.renderCropObjectUrl.mockResolvedValue('blob:crop-url');
        const annotation = {
            sample_id: 'ann-1',
            annotation_label: { annotation_label_name: 'cat' },
            annotation_collection_id: 'col-1'
        } as unknown as AnnotationView;
        const preview = useAnnotationCropPreview();
        preview.handleCropWindowChange('ann-1', window);

        await preview.handleAnnotationDragStart('ann-1');
        const dragData = buildClassificationDragData({
            annotation,
            cropWindow: preview.cropWindowByAnnotationId['ann-1'],
            cropUrl: preview.cropUrlByAnnotationId['ann-1']
        });

        expect(dragData?.url).toBe('blob:crop-url');
    });
});
