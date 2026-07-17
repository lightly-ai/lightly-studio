import {
    SampleType,
    type AnnotationWithPayloadView,
    type ImageAnnotationView,
    type VideoFrameAnnotationView
} from '$lib/api/lightly_studio_local';
import {
    getGridImageURL,
    getGridFrameURL,
    getGridThumbnailRequestSize,
    type GridThumbnailQuality
} from '$lib/utils';

type GetThumbnailUrlParams = {
    annotation: AnnotationWithPayloadView;
    quality: GridThumbnailQuality;
    containerWidth: number;
    containerHeight: number;
    cachedCollectionVersion: string;
};

/**
 * Returns the thumbnail URL for a classification annotation's parent sample.
 *
 * Dispatches to the image or video-frame URL helper based on `parent_sample_type`,
 * scaling the requested resolution to the rendered container size × device pixel ratio.
 */
export function getThumbnailUrl({
    annotation,
    quality,
    containerWidth,
    containerHeight,
    cachedCollectionVersion
}: GetThumbnailUrlParams): string {
    const dpr = globalThis.window?.devicePixelRatio || 1;
    const renderedWidth = getGridThumbnailRequestSize(containerWidth, dpr);
    const renderedHeight = getGridThumbnailRequestSize(containerHeight, dpr);
    if (annotation.parent_sample_type === SampleType.IMAGE) {
        const image = annotation.parent_sample_data as ImageAnnotationView;
        return getGridImageURL({
            sampleId: image.sample_id,
            quality,
            renderedWidth,
            renderedHeight,
            cacheBuster: cachedCollectionVersion
        });
    }
    const frame = annotation.parent_sample_data as VideoFrameAnnotationView;
    return getGridFrameURL({
        sampleId: frame.sample_id,
        quality,
        renderedWidth,
        renderedHeight
    });
}

/**
 * Returns the original pixel dimensions of the parent sample.
 *
 * For images this is the stored image size; for video frames it is the video
 * resolution. Used to express the full-image CropWindow in original coordinates.
 */
export function getSampleDimensions(annotation: AnnotationWithPayloadView): {
    width: number;
    height: number;
} {
    if (annotation.parent_sample_type === SampleType.IMAGE) {
        const image = annotation.parent_sample_data as ImageAnnotationView;
        return { width: image.width, height: image.height };
    }
    const frame = annotation.parent_sample_data as VideoFrameAnnotationView;
    return { width: frame.video.width, height: frame.video.height };
}
