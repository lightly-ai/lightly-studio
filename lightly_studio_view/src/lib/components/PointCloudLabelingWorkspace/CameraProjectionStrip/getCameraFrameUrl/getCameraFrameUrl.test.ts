import { describe, expect, it } from 'vitest';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import { getCameraFrameUrl } from './getCameraFrameUrl';

describe('getCameraFrameUrl', () => {
    const defaultParams = {
        datasetId: 'dataset-1',
        recordingId: 'recording-1',
        channelId: 3,
        timestampNs: 1234567890
    };

    it("builds the camera-frame URL from the client's base URL and route template", () => {
        const baseUrl = client.getConfig().baseUrl;

        expect(getCameraFrameUrl(defaultParams)).toBe(
            `${baseUrl}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=3&keyframe_timestamp_ns=1234567890`
        );
    });

    it('encodes dataset and recording ids that contain unsafe characters', () => {
        const url = getCameraFrameUrl({
            ...defaultParams,
            datasetId: 'data set/1',
            recordingId: 'rec#1'
        });

        expect(url).toContain('/datasets/data%20set%2F1/');
        expect(url).toContain('/recordings/rec%231/');
    });
});
