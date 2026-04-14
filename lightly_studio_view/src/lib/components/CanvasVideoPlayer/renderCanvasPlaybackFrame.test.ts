import { describe, expect, it, vi } from 'vitest';
import type { FrameView } from '$lib/api/lightly_studio_local';
import * as maskRendererUtils from '$lib/workers/maskRendererUtils';
import {
    buildPlaybackAnnotationPayload,
    renderCanvasPlaybackFrame
} from './renderCanvasPlaybackFrame';

describe('buildPlaybackAnnotationPayload', () => {
    it('collects segmentation masks and bounding boxes from a frame', () => {
        const frame = {
            sample_id: 'frame-1',
            frame_number: 1,
            frame_timestamp_s: 0.1,
            sample: {
                annotations: [
                    {
                        annotation_type: 'instance_segmentation',
                        annotation_label: { annotation_label_name: 'elephant' },
                        segmentation_details: {
                            x: 10,
                            y: 20,
                            width: 30,
                            height: 40,
                            segmentation_mask: [0, 2, 2]
                        }
                    },
                    {
                        annotation_type: 'object_detection',
                        annotation_label: { annotation_label_name: 'elephant' },
                        object_detection_details: {
                            x: 11,
                            y: 21,
                            width: 31,
                            height: 41
                        }
                    }
                ]
            }
        } as unknown as FrameView;

        const payload = buildPlaybackAnnotationPayload({
            frame,
            showBoundingBoxesForSegmentation: true,
            customLabelColors: {}
        });

        expect(payload.masks).toHaveLength(1);
        expect(payload.boxes).toHaveLength(2);
    });
});

describe('renderCanvasPlaybackFrame', () => {
    it('draws the video frame before masks and boxes', () => {
        vi.spyOn(maskRendererUtils, 'renderMasks').mockReturnValue(new Uint8ClampedArray(16));
        const drawBoxesSpy = vi.spyOn(maskRendererUtils, 'drawBoxesOnContext');

        const mainCtx = {
            clearRect: vi.fn(),
            drawImage: vi.fn(),
            save: vi.fn(),
            restore: vi.fn(),
            strokeRect: vi.fn(),
            lineWidth: 1,
            strokeStyle: ''
        } as unknown as CanvasRenderingContext2D;
        const maskCtx = {
            clearRect: vi.fn(),
            putImageData: vi.fn()
        } as unknown as CanvasRenderingContext2D;
        const mediaSource = {} as HTMLImageElement;
        const maskCanvas = {} as HTMLCanvasElement;

        renderCanvasPlaybackFrame({
            canvasCtx: mainCtx,
            maskCtx,
            maskCanvas,
            mediaSource,
            sampleWidth: 2,
            sampleHeight: 2,
            payload: {
                masks: [{ rle: [0, 2, 2], color: [0, 255, 0, 128] }],
                boxes: [{ x: 0, y: 0, width: 1, height: 1, color: [0, 255, 0, 255] }]
            }
        });

        expect(
            (mainCtx.clearRect as ReturnType<typeof vi.fn>).mock.invocationCallOrder[0]
        ).toBeLessThan((mainCtx.drawImage as ReturnType<typeof vi.fn>).mock.invocationCallOrder[0]);
        expect((mainCtx.drawImage as ReturnType<typeof vi.fn>).mock.calls[0]?.[0]).toBe(
            mediaSource
        );
        expect((mainCtx.drawImage as ReturnType<typeof vi.fn>).mock.calls[1]?.[0]).toBe(maskCanvas);
        expect(maskCtx.putImageData).toHaveBeenCalledTimes(1);
        expect(drawBoxesSpy).toHaveBeenCalledTimes(1);
    });
});
