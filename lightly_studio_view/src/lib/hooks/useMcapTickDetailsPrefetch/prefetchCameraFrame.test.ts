import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCameraFrame } from '$lib/api/lightly_studio_local/sdk.gen';
import { prefetchCameraFrame } from './prefetchCameraFrame';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getCameraFrame: vi.fn().mockResolvedValue({ data: new ArrayBuffer(0) })
}));

const channel = {
    channel_id: 7,
    group_component_name: 'front',
    group_component_index: 0
};

const frame = {
    channel_id: 7,
    group_component_name: 'front',
    log_time_ns: '2010',
    keyframe_log_time_ns: '2000'
};

describe('prefetchCameraFrame', () => {
    beforeEach(() => vi.clearAllMocks());

    it('requests the camera frame with nanosecond timestamps', async () => {
        await prefetchCameraFrame({
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channel,
            frame
        });

        expect(getCameraFrame).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', recording_id: 'recording-1' },
            query: {
                channel_id: 7,
                keyframe_timestamp_ns: '2000',
                log_time_ns: '2010'
            },
            parseAs: 'arrayBuffer',
            throwOnError: true
        });
    });

    it.each([
        { label: 'missing frame', frame: undefined },
        { label: 'missing keyframe', frame: { ...frame, keyframe_log_time_ns: null } }
    ])('skips the request when there is a $label', async ({ frame: missingFrame }) => {
        await prefetchCameraFrame({
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channel,
            frame: missingFrame
        });
        expect(getCameraFrame).not.toHaveBeenCalled();
    });
});
