import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { getColorByLabel } from '$lib/utils';
import SampleDetailsImageContainer from './SampleDetailsImageContainer.svelte';

const enforceColoringByClassStore = writable(false);
const annotations: AnnotationView[] = ['reference', 'prediction'].map((source) => ({
    sample_id: source,
    parent_sample_id: 'image',
    annotation_collection_id: source,
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'car' },
    object_detection_details: { x: 1, y: 2, width: 15, height: 16 },
    created_at: new Date()
}));

vi.mock('$app/navigation', () => ({ afterNavigate: vi.fn() }));
vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({
        enforceColoringByClassStore,
        settingsStore: writable({ key_hide_annotations: 'v' }),
        showAnnotationTextLabelsStore: writable(false),
        showBoundingBoxesForSegmentationStore: writable(true)
    })
}));
vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: (getParams: () => { annotationId: string }) => ({
        annotation: { data: annotations.find((a) => a.sample_id === getParams().annotationId) },
        updateAnnotation: vi.fn()
    })
}));
vi.mock('$lib/hooks/useAssistedLabelingStatus', () => ({
    useAssistedLabelingStatus: () => ({ disabledReason: null })
}));
vi.mock('$lib/components/SampleDetails/SmartSelectOverlay/useSmartSelect.svelte', () => ({
    useSmartSelect: () => ({ clear: vi.fn() })
}));
vi.mock('$lib/components/SampleDetails/FindInstancesOverlay/useFindInstances.svelte', () => ({
    useFindInstances: () => ({ clear: vi.fn() })
}));
// jsdom lacks the SVG matrix operations used to keep labels the same size while zooming.
vi.mock('$lib/components/ZoomableContainer/unscale', () => ({ unscale: vi.fn() }));

const defaultProps = {
    sample: { width: 100, height: 100, annotations, sampleId: 'image' },
    collectionId: 'images',
    imageUrl: '/image.jpg',
    hideAnnotationsIds: new Set<string>(),
    isResizable: false,
    isEraser: false,
    selectedAnnotationId: null,
    brushRadius: 10,
    annotationType: 'object_detection',
    refetch: vi.fn(),
    toggleAnnotationSelection: vi.fn()
};

describe('SampleDetailsImageContainer', () => {
    beforeEach(() => {
        const sources = useAnnotationCollectionsFilter();
        sources.setCollectionIdToName({ reference: 'Reference', prediction: 'Prediction' });
        sources.setSelectedCollectionIds(['reference', 'prediction']);
        // jsdom does not implement the text measurements used to size annotation labels.
        Object.defineProperty(SVGElement.prototype, 'getBBox', {
            configurable: true,
            value: () => ({ x: 0, y: 0, width: 30, height: 12 })
        });
    });
    afterEach(() => Reflect.deleteProperty(SVGElement.prototype, 'getBBox'));

    it.each([false, true])(
        'keeps colors and text when hiding annotations, class colors=%s',
        async (byClass) => {
            enforceColoringByClassStore.set(byClass);
            const { rerender } = render(SampleDetailsImageContainer, {
                props: defaultProps,
                context: new Map<string, unknown>([
                    ['annotation-label', {}],
                    ['sample-details-toolbar-type', { status: 'cursor' }]
                ])
            });
            const expectedColor = getColorByLabel(byClass ? 'car' : 'Reference', 1).color;
            expect(screen.getAllByTestId('annotation_box')[0]).toHaveAttribute(
                'stroke',
                expectedColor
            );
            expect(screen.getAllByTestId('svg-annotation-text')).toHaveLength(2);

            await rerender({ ...defaultProps, hideAnnotationsIds: new Set(['prediction']) });
            expect(screen.getAllByTestId('annotation_box')).toHaveLength(1);
            expect(screen.getByTestId('annotation_box')).toHaveAttribute('stroke', expectedColor);
            expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('car');
        }
    );
});
