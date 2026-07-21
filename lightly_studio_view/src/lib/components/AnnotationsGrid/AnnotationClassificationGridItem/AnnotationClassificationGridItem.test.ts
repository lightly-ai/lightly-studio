import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { tick } from 'svelte';
import { type Writable } from 'svelte/store';
import {
    SampleType,
    AnnotationType,
    type AnnotationWithPayloadView,
    type ImageAnnotationView,
    type VideoFrameAnnotationView,
    type AnnotationView
} from '$lib/api/lightly_studio_local';
import AnnotationClassificationGridItem from './AnnotationClassificationGridItem.svelte';

const mocks = vi.hoisted(() => ({
    selectedCollectionIds: null as unknown as Writable<string[]>
}));

vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', async () => {
    const { writable } = await import('svelte/store');
    mocks.selectedCollectionIds = writable<string[]>([]);
    return {
        useAnnotationCollectionsFilter: () => ({
            selectedCollectionIds: mocks.selectedCollectionIds,
            collectionIdToName: writable<Record<string, string>>({})
        })
    };
});

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    return {
        useSettings: vi.fn(() => ({
            gridViewThumbnailQualityStore: writable('raw'),
            enforceColoringByClassStore: writable(false)
        }))
    };
});

vi.mock('$lib/utils', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/utils')>();
    return {
        ...actual,
        getGridImageURL: ({ sampleId }: { sampleId: string }) => `http://images/sample/${sampleId}`,
        getGridFrameURL: ({ sampleId }: { sampleId: string }) => `http://frames/media/${sampleId}`
    };
});

function buildAnnotation(
    overrides: Partial<AnnotationWithPayloadView> = {}
): AnnotationWithPayloadView {
    return {
        parent_sample_type: SampleType.IMAGE,
        annotation: {
            sample_id: 'ann-1',
            annotation_type: AnnotationType.CLASSIFICATION,
            annotation_label: { annotation_label_name: 'cat' },
            annotation_collection_id: 'col-1',
            parent_sample_id: 'img-1'
        } as unknown as AnnotationView,
        parent_sample_data: {
            sample_id: 'img-1',
            width: 800,
            height: 600
        } as unknown as ImageAnnotationView,
        ...overrides
    };
}

const defaultProps = {
    containerWidth: 200,
    containerHeight: 150,
    cachedCollectionVersion: 'v1'
};

function renderItem(annotation: AnnotationWithPayloadView, props: Record<string, unknown> = {}) {
    return render(AnnotationClassificationGridItem, {
        props: { annotation, ...defaultProps, ...props }
    });
}

describe('AnnotationClassificationGridItem', () => {
    beforeEach(() => {
        mocks.selectedCollectionIds.set([]);
    });

    it('renders thumbnail div and classification pill for an image annotation', async () => {
        const { container } = renderItem(buildAnnotation());

        await tick();

        const thumbnail = container.firstElementChild as HTMLElement;
        expect(thumbnail).toBeInTheDocument();
        expect(thumbnail.style.backgroundImage).toContain('img-1');
        expect(screen.getAllByText('cat').length).toBeGreaterThan(0);
    });

    it('renders thumbnail using frame URL for a video frame annotation', async () => {
        const annotation = buildAnnotation({
            parent_sample_type: SampleType.VIDEO_FRAME,
            parent_sample_data: {
                sample_id: 'frame-1',
                video: { width: 1920, height: 1080, file_path_abs: '/video.mp4' }
            } as unknown as VideoFrameAnnotationView
        });
        const { container } = renderItem(annotation);

        await tick();

        const thumbnail = container.firstElementChild as HTMLElement;
        expect(thumbnail.style.backgroundImage).toContain('frames/media/frame-1');
    });

    it('applies grid-item-selected class when selected is true', () => {
        const { container } = renderItem(buildAnnotation(), { selected: true });

        expect(container.firstElementChild).toHaveAttribute('aria-selected', 'true');
    });

    it('always renders classification pill regardless of label visibility settings', async () => {
        renderItem(buildAnnotation());

        await tick();

        // The badge is the primary visual indicator for classification — it shows unconditionally,
        // unlike OD where the bounding box can be shown without the text label.
        expect(screen.getAllByText('cat').length).toBeGreaterThan(0);
    });

    it('passes only the single annotation label to SampleClassificationPills', async () => {
        renderItem(buildAnnotation());

        await tick();

        // Exactly one annotation is passed — not all sibling labels for the parent sample.
        // SampleClassificationPills renders two pill DOM elements (visible + hidden measurement
        // overlay) when pills are present; both should carry the single label 'cat'.
        expect(screen.getAllByText('cat')).toHaveLength(2);
    });

    it('shows classification pill even when the active source filter excludes the annotation collection', async () => {
        // The hook reports a non-matching collection; without the selectedCollectionIds=[] override
        // on the component, SampleClassificationPills would filter out 'col-1' and render nothing.
        mocks.selectedCollectionIds.set(['other-col']);

        renderItem(buildAnnotation());

        await tick();

        expect(screen.getAllByText('cat').length).toBeGreaterThan(0);
    });

    it('calls onCropWindowChange with a full-image CropWindow (windowX/Y=0) once URL is available', async () => {
        const onCropWindowChange = vi.fn();
        const annotation = buildAnnotation({
            parent_sample_data: {
                sample_id: 'img-1',
                width: 1024,
                height: 768
            } as unknown as ImageAnnotationView
        });

        renderItem(annotation, { onCropWindowChange });

        await tick();

        expect(onCropWindowChange).toHaveBeenCalledOnce();
        const [annotationId, cropWindow] = onCropWindowChange.mock.calls[0];
        expect(annotationId).toBe('ann-1');
        expect(cropWindow.windowX).toBe(0);
        expect(cropWindow.windowY).toBe(0);
        expect(cropWindow.windowWidth).toBe(1024);
        expect(cropWindow.windowHeight).toBe(768);
        expect(cropWindow.sampleWidth).toBe(1024);
        expect(cropWindow.sampleHeight).toBe(768);
    });

    it('calls onCropWindowChange with null on unmount', async () => {
        const onCropWindowChange = vi.fn();

        const { unmount } = renderItem(buildAnnotation(), { onCropWindowChange });

        await tick();
        unmount();
        await tick();

        const lastCall = onCropWindowChange.mock.calls.at(-1);
        expect(lastCall?.[0]).toBe('ann-1');
        expect(lastCall?.[1]).toBeNull();
    });
});
