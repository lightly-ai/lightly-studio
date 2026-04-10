import type { FrameView, SampleView, AnnotationView } from '$lib/api/lightly_studio_local';
import { getColorByLabel } from '$lib/utils';
import calculateBinaryMaskFromRLE from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE';

interface FrameAnnotationDataURL {
    frameId: string;
    annotationId: string;
    dataUrl: string;
    width: number;
    height: number;
}

/**
 * Pre-renders annotation masks for video frames as data URLs for efficient rendering.
 *
 * This hook processes all frames and their segmentation annotations, converting them
 * into ready-to-use data URLs. This avoids re-rendering segmentation masks on every
 * frame change during video playback.
 *
 * @param params - Configuration object
 * @param params.frames - Array of video frames with their annotations
 * @param params.imageWidth - Width of the video frames
 *
 * @returns Map of frame IDs to arrays of their pre-rendered annotation data URLs
 *
 * @example
 * ```ts
 * const { frames } = useVideoFrames({ video });
 * const frameAnnotations = useVideoFrameAnnotations({ frames, imageWidth: video.width });
 * const currentAnnotations = frameAnnotations.get(currentFrame.sample_id);
 * ```
 */
export function useVideoFrameAnnotations({
    frames,
    imageWidth
}: {
    frames: FrameView[];
    imageWidth: number;
}): Map<string, FrameAnnotationDataURL[]> {
    const annotationDataUrls = new Map<string, FrameAnnotationDataURL[]>();
    for (const frame of frames) {
        const sample = frame.sample as SampleView;
        const annotations: AnnotationView[] = sample.annotations ?? [];

        // Find all segmentation annotations with masks
        const segmentationAnnotations = annotations.filter(
            (annotation) =>
                annotation.annotation_type === 'instance_segmentation' &&
                annotation.segmentation_details?.segmentation_mask
        );

        const frameAnnotations: FrameAnnotationDataURL[] = [];

        for (const segmentationAnnotation of segmentationAnnotations) {
            if (segmentationAnnotation?.segmentation_details?.segmentation_mask) {
                const label = segmentationAnnotation.annotation_label.annotation_label_name;
                const colorFill = getColorByLabel(label, 0.4).color;

                // Convert to opaque color (same logic as SampleAnnotationSegmentationRLE)
                const opaqueColor = colorFill.replace(
                    /rgba?\((\d+,\s*\d+,\s*\d+)(?:,\s*[\d.]+)?\)/,
                    'rgb($1)'
                );

                try {
                    const { dataUrl, height } = calculateBinaryMaskFromRLE(
                        segmentationAnnotation.segmentation_details.segmentation_mask,
                        imageWidth,
                        opaqueColor
                    );

                    frameAnnotations.push({
                        frameId: frame.sample_id,
                        annotationId: segmentationAnnotation.sample_id,
                        dataUrl,
                        width: imageWidth,
                        height
                    });
                } catch (error) {
                    console.error(
                        `Failed to render annotation for frame ${frame.sample_id}:`,
                        error
                    );
                }
            }
        }

        if (frameAnnotations.length > 0) {
            annotationDataUrls.set(frame.sample_id, frameAnnotations);
        }
    }

    return annotationDataUrls;
}
