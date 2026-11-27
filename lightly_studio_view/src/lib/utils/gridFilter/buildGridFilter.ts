import type {
    ImageFilter,
    SampleFilter,
    VideoFilter,
    VideoFrameFilter
} from '$lib/api/lightly_studio_local';
import { withoutUndefined } from './withoutUndefined';

export type GridFilterByType = {
    image: ImageFilter;
    video: VideoFilter;
    video_frame: VideoFrameFilter;
};

/**
 * Builds a grid filter of the given type. Fields that are `undefined` are left out, and
 * `sample_filter` is set only when defined.
 */
export function buildGridFilter<T extends keyof GridFilterByType>(
    filterType: T,
    fields: Omit<GridFilterByType[T], 'filter_type' | 'sample_filter'>,
    sampleFilter: SampleFilter | undefined
): GridFilterByType[T] & { filter_type: T } {
    return withoutUndefined({
        ...fields,
        filter_type: filterType,
        sample_filter: sampleFilter
    }) as GridFilterByType[T] & { filter_type: T };
}
