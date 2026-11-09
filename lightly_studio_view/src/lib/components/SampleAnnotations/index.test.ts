import { render, waitFor } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import type { Readable, Writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SampleAnnotations from './index.svelte';
import { useSettings } from '$lib/hooks/useSettings';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { useAnnotationClassVisibility } from '$lib/hooks/useAnnotationClassVisibility/useAnnotationClassVisibility';
import { useCustomSourceColors } from '$lib/hooks';
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
        image_interpolation: true,
        key_hide_annotations: 'v',
        key_go_back: 'Escape',
        key_toggle_edit_mode: 'e',
        show_annotation_text_labels: false,
        show_sample_filenames: true,
        show_bounding_boxes_for_segmentation: true,
        annotation_color_mode: 'source',
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

const SAMPLE_SOURCE_ID = 'col-default';

const createSample = (): ComponentProps<typeof SampleAnnotations>['sample'] =>
    ({
        width: 100,
        height: 80,
        annotations: [
            {
                sample_id: 'object-detection-1',
                annotation_collection_id: SAMPLE_SOURCE_ID,
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
                annotation_collection_id: SAMPLE_SOURCE_ID,
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

const parseColorBytes = (color: string): [number, number, number, number] => {
    const hex = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(color);
    if (hex) return [parseInt(hex[1], 16), parseInt(hex[2], 16), parseInt(hex[3], 16), 255];
    const [r, g, b, a = 1] = color.match(/[\d.]+/g)!.map(Number);
    return [r, g, b, Math.round(a * 255)];
};

// Canvas contexts normalize color strings, so compare the channels only.
const normalizeColor = (color: string): string => color.replace(/\s+/g, '');

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
        const { setSelectedCollectionIds, setCollectionIdToName } =
            useAnnotationCollectionsFilter();
        setCollectionIdToName({ [SAMPLE_SOURCE_ID]: 'Ground truth' });
        setSelectedCollectionIds([SAMPLE_SOURCE_ID]);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
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

    it('draws nothing once the user unchecks every annotation source', async () => {
        vi.useFakeTimers();
        setShowBoundingBoxesForSegmentation(true);
        useAnnotationCollectionsFilter().setSelectedCollectionIds([]);

        render(SampleAnnotations, {
            props: {
                sample: createSample()
            }
        });

        // The canvas mounts from an idle callback; drain it before asserting nothing drew.
        await vi.runAllTimersAsync();

        expect(mockContext.strokeRect).not.toHaveBeenCalled();
    });

    // On the videos grid the frame annotations come from the frames collection, which is not
    // among the videos collection's own sources, so the filter must leave them alone.
    it('keeps drawing annotations from a source the filter does not know about', async () => {
        setShowBoundingBoxesForSegmentation(true);
        const { setSelectedCollectionIds, setCollectionIdToName } =
            useAnnotationCollectionsFilter();
        setCollectionIdToName({});
        setSelectedCollectionIds([]);

        render(SampleAnnotations, {
            props: {
                sample: createSample()
            }
        });

        await waitFor(() => {
            expect(hasStrokeRectCall(mockContext, 10, 21, 30, 41)).toBe(true);
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

    it('draws by the tree eyes per source and class when they are given', async () => {
        setShowBoundingBoxesForSegmentation(true);
        // The tree replaces the class eye and the source selection.
        useAnnotationClassVisibility().toggleClassVisibility('person');
        useAnnotationCollectionsFilter().setSelectedCollectionIds([]);
        const sample = createSample();
        sample.annotations = [
            {
                ...sample.annotations[0],
                sample_id: 'labels-car',
                annotation_collection_id: 'labels'
            },
            {
                ...sample.annotations[0],
                sample_id: 'model-car',
                annotation_collection_id: 'model_v1',
                object_detection_details: { x: 50, y: 50, width: 10, height: 10 }
            },
            sample.annotations[1]
        ];

        render(SampleAnnotations, {
            props: {
                sample,
                isAnnotationVisible: (annotation) =>
                    !(
                        annotation.annotation_collection_id === 'labels' &&
                        annotation.annotation_label.annotation_label_name === 'car'
                    )
            }
        });

        await waitFor(() => {
            expect(hasStrokeRectCall(mockContext, 50, 50, 10, 10)).toBe(true);
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
            const colorBySourceSpy = vi.spyOn(utils, 'getColorBySource');

            setSelectedCollectionIds(['col-a', 'col-b']);
            setCollectionIdToName({ 'col-a': 'GroundTruth', 'col-b': 'Predictions' });
            setEnforceColoringByClass(false);

            render(SampleAnnotations, { props: { sample: createTwoSourceSample() } });

            await waitFor(() => {
                const calledNames = colorBySourceSpy.mock.calls.map(([name]) => name);
                expect(calledNames).toContain('GroundTruth');
                expect(calledNames).toContain('Predictions');
            });

            colorBySourceSpy.mockRestore();
        });

        it('colors by class when multiple sources are selected and enforce is enabled', async () => {
            const { setCustomColor, clearCustomColors } = useCustomSourceColors();
            setCustomColor('GroundTruth', '#ff0000', 1);
            setCustomColor('Predictions', '#ff0000', 1);
            // The canvas parses colors by painting one pixel, so make the mock paint for real.
            let lastFillStyle = '';
            Object.defineProperty(mockContext, 'fillStyle', {
                get: () => lastFillStyle,
                set: (value: string) => {
                    lastFillStyle = value;
                }
            });
            mockContext.getImageData.mockImplementation(() => ({
                data: new Uint8ClampedArray(parseColorBytes(lastFillStyle))
            }));
            const strokeStyles: string[] = [];
            Object.defineProperty(mockContext, 'strokeStyle', {
                get: () => strokeStyles.at(-1) ?? '',
                set: (value: string) => strokeStyles.push(value)
            });

            setSelectedCollectionIds(['col-a', 'col-b']);
            setCollectionIdToName({ 'col-a': 'GroundTruth', 'col-b': 'Predictions' });
            setEnforceColoringByClass(true);

            render(SampleAnnotations, { props: { sample: createTwoSourceSample() } });

            try {
                await waitFor(() => {
                    expect(mockContext.strokeRect).toHaveBeenCalled();
                });
                // Both boxes are class "car", so they use the class color, not the source color.
                const classColor = utils.getColorByLabel('car', 1).color;
                expect(strokeStyles.length).toBeGreaterThan(0);
                expect(new Set(strokeStyles.map(normalizeColor))).toEqual(
                    new Set([normalizeColor(classColor)])
                );
                expect(strokeStyles.map(normalizeColor)).not.toContain('rgba(255,0,0,1)');
            } finally {
                clearCustomColors();
            }
        });
    });
});
