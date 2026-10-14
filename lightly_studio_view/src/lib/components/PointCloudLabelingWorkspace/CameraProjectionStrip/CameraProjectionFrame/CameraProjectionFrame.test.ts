import { render, screen } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/dom';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import CameraProjectionFrame from './CameraProjectionFrame.svelte';

// Pin the client's base URL so the enlarged frame src is deterministic regardless of the
// value baked into the generated client at build time (see getCameraFrameUrl.test.ts).
const TEST_BASE_URL = 'http://api.test';

const defaultProps = {
    datasetId: 'dataset-1',
    recordingId: 'recording-1',
    channelId: 3,
    keyframeTimestampNs: '1500',
    logTimeNs: '2000',
    blob: new Blob(['jpeg'], { type: 'image/jpeg' }),
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

    beforeEach(() => {
        // jsdom has no object URLs.
        URL.createObjectURL = vi.fn(() => 'blob:front');
        URL.revokeObjectURL = vi.fn();
    });

    it('renders the tick image of the frame with the caption', () => {
        render(CameraProjectionFrame, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toHaveAttribute('src', 'blob:front');
        expect(URL.createObjectURL).toHaveBeenCalledWith(defaultProps.blob);
        expect(screen.getByText('front')).toBeInTheDocument();
    });

    it('shows the placeholder without an image or when the image fails to load', async () => {
        const { unmount } = render(CameraProjectionFrame, {
            props: { ...defaultProps, blob: undefined }
        });
        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        unmount();

        render(CameraProjectionFrame, { props: defaultProps });
        await fireEvent.error(screen.getByRole('img', { name: 'front' }));

        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        expect(screen.getByText('front')).toBeInTheDocument();
    });

    it('enlarges the frame at full resolution in a dialog', async () => {
        render(CameraProjectionFrame, { props: defaultProps });

        await fireEvent.click(screen.getByRole('button', { name: 'Enlarge front' }));

        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByRole('img', { name: 'front enlarged' })).toHaveAttribute(
            'src',
            `${TEST_BASE_URL}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=3&keyframe_timestamp_ns=1500&log_time_ns=2000`
        );
        expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });
});
