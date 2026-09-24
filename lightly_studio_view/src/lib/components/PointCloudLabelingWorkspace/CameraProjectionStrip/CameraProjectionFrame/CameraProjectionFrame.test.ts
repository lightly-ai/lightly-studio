import { render, screen } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/dom';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import CameraProjectionFrame from './CameraProjectionFrame.svelte';

// Pin the client's base URL so the frame src is deterministic regardless of the
// value baked into the generated client at build time (see getCameraFrameUrl.test.ts).
const TEST_BASE_URL = 'http://api.test';

const defaultProps = {
    datasetId: 'dataset-1',
    recordingId: 'recording-1',
    channelId: 3,
    timestampNs: '2000',
    label: 'front'
};

describe('CameraProjectionFrame', () => {
    const originalBaseUrl = client.getConfig().baseUrl;

    beforeAll(() => {
        client.setConfig({ baseUrl: TEST_BASE_URL });
    });

    afterAll(() => {
        client.setConfig({ baseUrl: originalBaseUrl });
    });

    it('renders the frame image with the caption and a URL built from the props', () => {
        render(CameraProjectionFrame, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toHaveAttribute(
            'src',
            `${TEST_BASE_URL}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=3&keyframe_timestamp_ns=2000`
        );
        expect(screen.getByText('front')).toBeInTheDocument();
    });

    it('falls back to the placeholder when the frame image fails to load', async () => {
        render(CameraProjectionFrame, { props: defaultProps });

        const image = screen.getByRole('img', { name: 'front' });
        await fireEvent.error(image);

        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        expect(screen.getByText('front')).toBeInTheDocument();
    });
});
