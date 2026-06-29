import { render, waitFor } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import type { Readable, Writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SampleAnnotations from './index.svelte';
import { useSettings } from '$lib/hooks/useSettings';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { useAnnotationClassVisibility } from '$lib/hooks/useAnnotationClassVisibility/useAnnotationClassVisibility';
import * as utils from '$lib/utils';

type UseSettingsReturn = ReturnType<typeof useSettings>;
type SettingsStoreValue =
    UseSettingsReturn['settingsStore'] extends Writable<infer Value> ? Value : never;
type ShowBoundingBoxesForSegmentationValue =
    UseSettingsReturn['showBoundingBoxesForSegmentationStore'] extends Readable<infer Value>
        ? Value
        : never;
type MockedUseSettingsStoreSlice = Pick<
    UseSettingsReturn,
    'settingsStore' | 'showBoundingBoxesForSegmentationStore' | 'enforceColoringByClassStore'
>;
type MockUseSettingsControls = {
    setShowBoundingBoxesForSegmentation: (value: ShowBoundingBoxesForSegmentationValue) => void;
    setEnforceColoringByClass: (value: boolean) => void;
};

const mockUseSettingsControls: MockUseSettingsControls = vi.hoisted(() => ({
    setShowBoundingBoxesForSegmentation: () => {
        throw new Error('showBoundingBoxesForSegmentationStore is not initialized');
    },
    setEnforceColoringByClass: () => {
        throw new Error('enforceColoringByClassStore is not initialized');
    }
}));

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');

    const settingsStore = writable<SettingsStoreValue>({
        setting_id: '00000000-0000-0000-0000-000000000000',
        grid_view_sample_rendering: 'contain',
        grid_view_thumbnail_quality: 'raw',
        key_hide_annotations: 'v',
        key_go_back: 'Escape',
        key_toggle_edit_mode: 'e',
        show_annotation_text_labels: false,
        show_sample_filenames: true,
        show_bounding_boxes_for_segmentation: true,
        enforce_coloring_by_class: false,
        created_at: new Date('1970-01-01T00:00:00.000Z'),
        updated_at: new Date('1970-01-01T00:00:00.000Z'),
        key_toolbar_selection: 's',
        key_toolbar_drag: 'd',
        key_toolbar_bounding_box: 'b',
        key_toolbar_segmentation_mask: 'm',
        key_toolbar_brush: 'r',
        key_toolbar_eraser: 'x'
    });
    const showBoundingBoxesForSegmentationStore =
        writable<ShowBoundingBoxesForSegmentationValue>(true);
    const enforceColoringByClassStore = writable<boolean>(false);

    mockUseSettingsControls.setShowBoundingBoxesForSegmentation = (value) => {
        showBoundingBoxesForSegmentationStore.set(value);
    };
    mockUseSettingsControls.setEnforceColoringByClass = (value) => {
        enforceColoringByClassStore.set(value);
    };

    const mockedUseSettingsStoreSlice: MockedUseSettingsStoreSlice = {
        settingsStore,
        showBoundingBoxesForSegmentationStore,
        enforceColoringByClassStore
    };

    return {
        useSettings: () => mockedUseSettingsStoreSlice
    };
});

type Mock2dContext = {
    fillStyle: string;
    strokeStyle: string;
    lineWidth: number;
    clearRect: ReturnType<typeof vi.fn>;
    fillRect: ReturnType<typeof vi.fn>;
    getImageData: ReturnType<typeof vi.fn>;
    putImageData: ReturnType<typeof vi.fn>;
    save: ReturnType<typeof vi.fn>;
    restore: ReturnType<typeof vi.fn>;
    strokeRect: ReturnType<typeof vi.fn>;
};

const createSample = (): ComponentProps<typeof SampleAnnotations>['sample'] =>
    ({
        width: 100,
        height: 80,
        annotations: [
            {
                sample_id: 'object-detection-1',
                annotation_type: 'object_detection',
                annotation_label: { annotation_label_name: 'car' },
                object_detection_details: {
                    x: 10.2,
                    y: 20.6,
                    width: 30.4,
                    height: 40.9
                }
            },
            {
                sample_id: 'instance-segmentation-1',
                annotation_type: 'segmentation_mask',
                annotation_label: { annotation_label_name: 'person' },
                segmentation_details: {
                    x: 2,
                    y: 3,
                    width: 4,
                    height: 5,
                    segmentation_mask: []
                }
            }
        ]
    }) as ComponentProps<typeof SampleAnnotations>['sample'];

const hasStrokeRectCall = (
    mockContext: Mock2dContext,
    x: number,
    y: number,
    width: number,
    height: number
): boolean => {
    return mockContext.strokeRect.mock.calls.some(
        ([callX, callY, callWidth, callHeight]) =>
            callX === x && callY === y && callWidth === width && callHeight === height
    );
};

const setShowBoundingBoxesForSegmentation = (value: ShowBoundingBoxesForSegmentationValue) => {
    mockUseSettingsControls.setShowBoundingBoxesForSegmentation(value);
};

const setEnforceColoringByClass = (value: boolean) => {
    mockUseSettingsControls.setEnforceColoringByClass(value);
};

describe('SampleAnnotations', () => {
    let mockContext: Mock2dContext;

    beforeEach(() => {
        mockContext = {
            fillStyle: 'rgba(0, 0, 0, 0)',
            strokeStyle: 'rgba(0, 0, 0, 0)',
            lineWidth: 1,
            clearRect: vi.fn(),
            fillRect: vi.fn(),
            getImageData: vi.fn(() => ({ data: new Uint8ClampedArray([10, 20, 30, 128]) })),
            putImageData: vi.fn(),
            save: vi.fn(),
            restore: vi.fn(),
            strokeRect: vi.fn()
        };

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
            (contextId: string) => {
                if (contextId !== '2d') {
                    return null;
                }

                return mockContext as unknown as CanvasRenderingContext2D;
            }
        );

        useAnnotationClassVisibility().hiddenClassNamesStore.set([]);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('keeps object-detection boxes visible when showBoundingBoxesForSegmentation is disabled', async () => {
        setShowBoundingBoxesForSegmentation(false);

        render(SampleAnnotations, {
            props: {
                sample: createSample()
            }
        });

        await waitFor(() => {
            expect(mockContext.strokeRect).toHaveBeenCalled();
        });

        expect(hasStrokeRectCall(mockContext, 10, 21, 30, 41)).toBe(true);
        expect(hasStrokeRectCall(mockContext, 2, 3, 4, 5)).toBe(false);
    });

    it('shows instance-segmentation bounding boxes when showBoundingBoxesForSegmentation is enabled', async () => {
        setShowBoundingBoxesForSegmentation(true);

        render(SampleAnnotations, {
            props: {
                sample: createSample()
            }
        });

        await waitFor(() => {
            expect(hasStrokeRectCall(mockContext, 10, 21, 30, 41)).toBe(true);
            expect(hasStrokeRectCall(mockContext, 2, 3, 4, 5)).toBe(true);
        });
    });

    it('does not render annotations for hidden classes', async () => {
        setShowBoundingBoxesForSegmentation(true);
        useAnnotationClassVisibility().toggleClassVisibility('car');

        render(SampleAnnotations, {
            props: {
                sample: createSample()
            }
        });

        await waitFor(() => {
            expect(hasStrokeRectCall(mockContext, 2, 3, 4, 5)).toBe(true);
        });

        expect(hasStrokeRectCall(mockContext, 10, 21, 30, 41)).toBe(false);
    });

    describe('enforceColoringByClass setting', () => {
        const { setSelectedCollectionIds, setCollectionIdToName } =
            useAnnotationCollectionsFilter();

        const createTwoSourceSample = (): ComponentProps<typeof SampleAnnotations>['sample'] =>
            ({
                width: 100,
                height: 80,
                annotations: [
                    {
                        sample_id: 'obj-src-a',
                        annotation_collection_id: 'col-a',
                        annotation_type: 'object_detection',
                        annotation_label: { annotation_label_name: 'car' },
                        object_detection_details: { x: 1, y: 1, width: 10, height: 10 }
                    },
                    {
                        sample_id: 'obj-src-b',
                        annotation_collection_id: 'col-b',
                        annotation_type: 'object_detection',
                        annotation_label: { annotation_label_name: 'car' },
                        object_detection_details: { x: 20, y: 20, width: 10, height: 10 }
                    }
                ]
            }) as ComponentProps<typeof SampleAnnotations>['sample'];

        afterEach(() => {
            setSelectedCollectionIds([]);
            setCollectionIdToName({});
            setEnforceColoringByClass(false);
        });

        it('colors by source name when multiple sources are selected and enforce is disabled', async () => {
            const colorByLabelSpy = vi.spyOn(utils, 'getColorByLabel');

            setSelectedCollectionIds(['col-a', 'col-b']);
            setCollectionIdToName({ 'col-a': 'GroundTruth', 'col-b': 'Predictions' });
            setEnforceColoringByClass(false);

            render(SampleAnnotations, { props: { sample: createTwoSourceSample() } });

            await waitFor(() => {
                const calledNames = colorByLabelSpy.mock.calls.map(([name]) => name);
                expect(calledNames).toContain('GroundTruth');
                expect(calledNames).toContain('Predictions');
            });

            colorByLabelSpy.mockRestore();
        });

        it('colors by class when multiple sources are selected and enforce is enabled', async () => {
            const colorByLabelSpy = vi.spyOn(utils, 'getColorByLabel');

            setSelectedCollectionIds(['col-a', 'col-b']);
            setCollectionIdToName({ 'col-a': 'GroundTruth', 'col-b': 'Predictions' });
            setEnforceColoringByClass(true);

            render(SampleAnnotations, { props: { sample: createTwoSourceSample() } });

            await waitFor(() => {
                const calledNames = colorByLabelSpy.mock.calls.map(([name]) => name);
                expect(calledNames).toContain('car');
                expect(calledNames).not.toContain('GroundTruth');
                expect(calledNames).not.toContain('Predictions');
            });

            colorByLabelSpy.mockRestore();
        });
    });
});
