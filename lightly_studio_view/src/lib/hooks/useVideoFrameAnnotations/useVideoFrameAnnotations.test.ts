import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useVideoFrameAnnotations } from './useVideoFrameAnnotations';
import type { FrameView, SampleView, AnnotationView } from '$lib/api/lightly_studio_local';
import * as utils from '$lib/utils';
import * as calculateBinaryMaskModule from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE';

vi.mock('$lib/utils', async () => {
    const actual = await vi.importActual('$lib/utils');
    return {
        ...actual,
        getColorByLabel: vi.fn()
    };
});

vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE',
    async () => {
        const actual = await vi.importActual(
            '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE'
        );
        return {
            ...actual,
            default: vi.fn()
        };
    }
);

describe('useVideoFrameAnnotations', () => {
    const mockAnnotationLabel = {
        annotation_label_name: 'person',
        annotation_label_id: 'label-1',
        created_at: new Date(0)
    };

    const mockSegmentationAnnotation: AnnotationView = {
        sample_id: 'annotation-1',
        parent_sample_id: 'frame-1',
        annotation_type: 'instance_segmentation',
        annotation_label: mockAnnotationLabel,
        segmentation_details: {
            segmentation_mask: [10, 5, 3, 2],
            x: 0,
            y: 0,
            width: 100,
            height: 100
        },
        created_at: new Date(0)
    };

    const mockClassificationAnnotation: AnnotationView = {
        sample_id: 'annotation-2',
        parent_sample_id: 'frame-1',
        annotation_type: 'classification',
        annotation_label: mockAnnotationLabel,
        created_at: new Date(0)
    };

    const createMockFrame = (
        frameId: string,
        frameNumber: number,
        annotations: AnnotationView[] = []
    ): FrameView => {
        const sample: SampleView = {
            collection_id: 'frame-collection-1',
            sample_id: frameId,
            annotations,
            created_at: new Date(0),
            updated_at: new Date(0)
        };

        return {
            sample_id: frameId,
            frame_number: frameNumber,
            frame_timestamp_s: frameNumber / 30,
            sample
        } as FrameView;
    };

    beforeEach(() => {
        vi.clearAllMocks();

        // Default mock implementations
        vi.mocked(utils.getColorByLabel).mockReturnValue({
            color: 'rgba(255, 0, 0, 0.4)',
            contrastColor: '#FFFFFF'
        });

        vi.mocked(calculateBinaryMaskModule.default).mockReturnValue({
            dataUrl: 'data:image/png;base64,mockDataUrl',
            height: 100
        });
    });

    it('should return empty map for frames without annotations', () => {
        const frames = [
            createMockFrame('frame-1', 0),
            createMockFrame('frame-2', 1),
            createMockFrame('frame-3', 2)
        ];

        const result = useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        expect(result.size).toBe(0);
        expect(calculateBinaryMaskModule.default).not.toHaveBeenCalled();
    });

    it('should skip classification annotations', () => {
        const frames = [createMockFrame('frame-1', 0, [mockClassificationAnnotation])];

        const result = useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        expect(result.size).toBe(0);
        expect(calculateBinaryMaskModule.default).not.toHaveBeenCalled();
    });

    it('should generate dataURLs for frames with segmentation masks', () => {
        const frames = [
            createMockFrame('frame-1', 0, [mockSegmentationAnnotation]),
            createMockFrame('frame-2', 1, [mockSegmentationAnnotation])
        ];

        const result = useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        expect(result.size).toBe(2);
        expect(result.has('frame-1')).toBe(true);
        expect(result.has('frame-2')).toBe(true);

        const frame1Data = result.get('frame-1');
        expect(frame1Data).toEqual({
            frameId: 'frame-1',
            dataUrl: 'data:image/png;base64,mockDataUrl',
            width: 1920,
            height: 100
        });

        expect(calculateBinaryMaskModule.default).toHaveBeenCalledTimes(2);
    });

    it('should convert rgba color to rgb for mask rendering', () => {
        const frames = [createMockFrame('frame-1', 0, [mockSegmentationAnnotation])];

        useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        expect(calculateBinaryMaskModule.default).toHaveBeenCalledWith(
            [10, 5, 3, 2],
            1920,
            'rgb(255, 0, 0)'
        );
    });

    it('should handle frames with multiple annotations and use first segmentation', () => {
        const secondSegmentationAnnotation: AnnotationView = {
            sample_id: 'annotation-3',
            parent_sample_id: 'frame-1',
            annotation_type: 'instance_segmentation',
            annotation_label: { ...mockAnnotationLabel, annotation_label_name: 'car' },
            segmentation_details: {
                segmentation_mask: [5, 5, 5, 5],
                x: 0,
                y: 0,
                width: 100,
                height: 100
            },
            created_at: new Date(0)
        };

        const frames = [
            createMockFrame('frame-1', 0, [
                mockClassificationAnnotation,
                mockSegmentationAnnotation,
                secondSegmentationAnnotation
            ])
        ];

        useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        // Should only call once with the first segmentation annotation
        expect(calculateBinaryMaskModule.default).toHaveBeenCalledTimes(1);
        expect(utils.getColorByLabel).toHaveBeenCalledWith('person', 0.4);
    });

    it('should skip frames with segmentation annotation but no mask', () => {
        const annotationWithoutMask: AnnotationView = {
            ...mockSegmentationAnnotation,
            segmentation_details: undefined
        };

        const frames = [createMockFrame('frame-1', 0, [annotationWithoutMask])];

        const result = useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        expect(result.size).toBe(0);
        expect(calculateBinaryMaskModule.default).not.toHaveBeenCalled();
    });

    it('should handle errors gracefully and continue processing other frames', () => {
        const frames = [
            createMockFrame('frame-1', 0, [mockSegmentationAnnotation]),
            createMockFrame('frame-2', 1, [mockSegmentationAnnotation]),
            createMockFrame('frame-3', 2, [mockSegmentationAnnotation])
        ];

        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

        // Mock the second call to throw an error
        vi.mocked(calculateBinaryMaskModule.default)
            .mockReturnValueOnce({ dataUrl: 'data:image/png;base64,frame1', height: 100 })
            .mockImplementationOnce(() => {
                throw new Error('Failed to render mask');
            })
            .mockReturnValueOnce({ dataUrl: 'data:image/png;base64,frame3', height: 100 });

        const result = useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        // Should have processed frame-1 and frame-3, but not frame-2
        expect(result.size).toBe(2);
        expect(result.has('frame-1')).toBe(true);
        expect(result.has('frame-2')).toBe(false);
        expect(result.has('frame-3')).toBe(true);

        expect(consoleErrorSpy).toHaveBeenCalledWith(
            'Failed to render annotation for frame frame-2:',
            expect.any(Error)
        );

        consoleErrorSpy.mockRestore();
    });

    it('should use correct imageWidth for all frames', () => {
        const frames = [
            createMockFrame('frame-1', 0, [mockSegmentationAnnotation]),
            createMockFrame('frame-2', 1, [mockSegmentationAnnotation])
        ];

        const imageWidth = 3840; // 4K resolution
        const result = useVideoFrameAnnotations({ frames, imageWidth });

        expect(calculateBinaryMaskModule.default).toHaveBeenCalledWith(
            expect.any(Array),
            3840,
            expect.any(String)
        );

        const frame1Data = result.get('frame-1');
        expect(frame1Data?.width).toBe(3840);
    });

    it('should return Map for efficient O(1) lookup', () => {
        const frames = [createMockFrame('frame-1', 0, [mockSegmentationAnnotation])];

        const result = useVideoFrameAnnotations({ frames, imageWidth: 1920 });

        expect(result).toBeInstanceOf(Map);
        expect(result.get('frame-1')).toBeDefined();
        expect(result.get('non-existent')).toBeUndefined();
    });

    it('should handle empty frames array', () => {
        const result = useVideoFrameAnnotations({ frames: [], imageWidth: 1920 });

        expect(result.size).toBe(0);
        expect(calculateBinaryMaskModule.default).not.toHaveBeenCalled();
    });
});
