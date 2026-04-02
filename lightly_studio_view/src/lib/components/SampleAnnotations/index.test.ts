import { render, waitFor } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SampleAnnotations from './index.svelte';
import { useSettings } from '$lib/hooks/useSettings';

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');

    const settingsStore = writable({
        key_hide_annotations: 'v'
    });
    const showBoundingBoxesForSegmentationStore = writable(true);

    return {
        useSettings: () => ({
            settingsStore,
            showBoundingBoxesForSegmentationStore
        })
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
                annotation_type: 'instance_segmentation',
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

const setShowBoundingBoxesForSegmentation = (value: boolean) => {
    const { showBoundingBoxesForSegmentationStore } = useSettings();
    (showBoundingBoxesForSegmentationStore as unknown as { set: (enabled: boolean) => void }).set(
        value
    );
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
});
