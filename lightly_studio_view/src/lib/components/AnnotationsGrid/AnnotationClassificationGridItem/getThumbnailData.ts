import {
    SampleType,
    type ImageAnnotationView,
    type VideoFrameAnnotationView
} from '$lib/api/lightly_studio_local';
import { getGridImageURL, getGridFrameURL, getGridThumbnailRequestSize } from '$lib/utils';

type GridThumbnailQuality = Parameters<typeof getGridImageURL>[0]['quality'];

interface AnnotationSampleData {
    parent_sample_type: string;
    parent_sample_data: ImageAnnotationView | VideoFrameAnnotationView;
}

type GetThumbnailUrlParams = {
    annotation: AnnotationSampleData;
    quality: GridThumbnailQuality;
    containerWidth: number;
    containerHeight: number;
    cachedCollectionVersion: string;
};

interface SampleDimensions {
    width: number;
    height: number;
}

function getImageThumbnailUrl(
    image: ImageAnnotationView,
    quality: GridThumbnailQuality,
    renderedWidth: number,
    renderedHeight: number,
    cachedCollectionVersion: string
): string {
    return getGridImageURL({
        sampleId: image.sample_id,
        quality,
        renderedWidth,
        renderedHeight,
        cacheBuster: cachedCollectionVersion
    });
}

function getFrameThumbnailUrl(
    frame: VideoFrameAnnotationView,
    quality: GridThumbnailQuality,
    renderedWidth: number,
    renderedHeight: number
): string {
    return getGridFrameURL({ sampleId: frame.sample_id, quality, renderedWidth, renderedHeight });
}

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
        return getImageThumbnailUrl(
            annotation.parent_sample_data as ImageAnnotationView,
            quality,
            renderedWidth,
            renderedHeight,
            cachedCollectionVersion
        );
    }
    return getFrameThumbnailUrl(
        annotation.parent_sample_data as VideoFrameAnnotationView,
        quality,
        renderedWidth,
        renderedHeight
    );
}

// CropWindow is expressed in original sample coordinates
export function getSampleDimensions(annotation: AnnotationSampleData): SampleDimensions {
    if (annotation.parent_sample_type === SampleType.IMAGE) {
        const image = annotation.parent_sample_data as ImageAnnotationView;
        return { width: image.width, height: image.height };
    }
    const frame = annotation.parent_sample_data as VideoFrameAnnotationView;
    return { width: frame.video.width, height: frame.video.height };
}
