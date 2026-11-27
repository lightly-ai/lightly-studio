import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
import type { McapSequenceFrame } from '$lib/api/lightly_studio_local/types.gen';

/** Builds the URL of the camera frame that shows an MCAP sequence, scaled to the given size. */
export const getMcapSequenceFrameURL = (
    sequenceFrame: McapSequenceFrame,
    width: number,
    height: number
): string =>
    `${PUBLIC_LIGHTLY_STUDIO_API_URL}datasets/${sequenceFrame.dataset_id}/recordings/${sequenceFrame.recording_id}/camera-frame` +
    `?channel_id=${sequenceFrame.channel_id}` +
    `&keyframe_timestamp_ns=${sequenceFrame.keyframe_log_time_ns}` +
    `&w=${Math.round(width)}&h=${Math.round(height)}`;
