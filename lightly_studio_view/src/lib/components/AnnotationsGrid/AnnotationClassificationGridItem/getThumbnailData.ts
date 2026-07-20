import {
    SampleType,
    type AnnotationWithPayloadView,
    type ImageAnnotationView,
    type VideoFrameAnnotationView
} from '$lib/api/lightly_studio_local';
import { getGridImageURL, getGridFrameURL, getGridThumbnailRequestSize } from '$lib/utils';

type GridThumbnailQuality = Parameters<typeof getGridImageURL>[0]['quality'];

type GetThumbnailUrlParams = {
    annotation: AnnotationWithPayloadView;
    quality: GridThumbnailQuality;
    containerWidth: number;
    containerHeight: number;
    cachedCollectionVersion: string;
};

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

// CropWindow is expressed in original sample coordinates
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
