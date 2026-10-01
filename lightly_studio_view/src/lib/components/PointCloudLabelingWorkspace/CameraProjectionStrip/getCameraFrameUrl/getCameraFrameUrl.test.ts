import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import { getCameraFrameUrl } from './getCameraFrameUrl';

// Pin the client's base URL so the assertions don't depend on the value the client reads
// from PUBLIC_LIGHTLY_STUDIO_API_URL at runtime.
const TEST_BASE_URL = 'http://api.test';

describe('getCameraFrameUrl', () => {
    const originalBaseUrl = client.getConfig().baseUrl;

    beforeAll(() => {
        client.setConfig({ baseUrl: TEST_BASE_URL });
    });

    afterAll(() => {
        client.setConfig({ baseUrl: originalBaseUrl });
    });

    const defaultParams = {
        datasetId: 'dataset-1',
        recordingId: 'recording-1',
        channelId: 3,
        timestampNs: '1234567890'
    };

    it("builds the camera-frame URL from the client's base URL and route template", () => {
        expect(getCameraFrameUrl(defaultParams)).toBe(
            `${TEST_BASE_URL}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=3&keyframe_timestamp_ns=1234567890`
        );
    });

    it.each([
        { label: 'unset (missing env var)', baseUrl: undefined },
        { label: 'root', baseUrl: '/' },
        { label: 'host with a trailing slash', baseUrl: 'http://api.test/' }
    ])('emits a clean URL when the base URL is $label', ({ baseUrl }) => {
        client.setConfig({ baseUrl });

        const url = getCameraFrameUrl(defaultParams);

        expect(url).not.toContain('undefined');
        expect(url).not.toContain('//datasets');
        expect(url).toContain('/datasets/dataset-1/recordings/recording-1/camera-frame');
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
