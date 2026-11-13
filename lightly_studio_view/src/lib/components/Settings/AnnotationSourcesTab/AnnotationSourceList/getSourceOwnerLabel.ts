import { SampleType } from '$lib/api/lightly_studio_local';

interface SourceOwner {
    parent_sample_type: SampleType;
    parent_group_component_name?: string | null;
}

// The words the navigation menu uses for these collections.
const SAMPLE_TYPE_LABELS: Partial<Record<SampleType, string>> = {
    [SampleType.IMAGE]: 'Images',
    [SampleType.VIDEO]: 'Videos',
    [SampleType.VIDEO_FRAME]: 'Frames',
    [SampleType.GROUP]: 'Groups',
    [SampleType.SEQUENCE]: 'Point clouds'
};

/**
 * The short text after a source's name that says where the source lives, for example "Frames"
 * for a source under the video frames of a video dataset. A group component's name wins, because
 * components of the same type differ only by name.
 */
export const getSourceOwnerLabel = (source: SourceOwner): string =>
    source.parent_group_component_name ||
    SAMPLE_TYPE_LABELS[source.parent_sample_type] ||
    source.parent_sample_type;
