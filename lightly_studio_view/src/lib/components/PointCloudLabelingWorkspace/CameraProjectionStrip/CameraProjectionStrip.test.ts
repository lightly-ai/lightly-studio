import { render, screen } from '@testing-library/svelte';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import CameraProjectionStrip from './CameraProjectionStrip.svelte';

// The strip pulls the recording and per-channel locators from useTickDetails.
// Mock the hook's source module so the barrel (`$lib/hooks`) re-exports the stub,
// letting each test drive the query result without a live TanStack query.
const tickDetailsResult: { data: TickDetailView | undefined } = { data: undefined };
vi.mock('$lib/hooks/useTickDetails/useTickDetails.svelte', () => ({
    useTickDetails: () => ({ tickDetails: tickDetailsResult })
}));

// Pin the client base URL so the child frame's `src` is deterministic
// (see CameraProjectionFrame.test.ts / getCameraFrameUrl.test.ts).
const TEST_BASE_URL = 'http://api.test';

const cameraChannels = [
    { channel_id: 1, group_component_name: 'front', group_component_index: 0 },
    { channel_id: 2, group_component_name: 'rear', group_component_index: 1 },
    { channel_id: 3, group_component_name: 'side', group_component_index: 2 }
];

const defaultProps = {
    datasetId: 'dataset-1',
    sequenceId: 'sequence-1',
    seqNumber: 0,
    cameraChannels
};

const tickDetails: TickDetailView = {
    recording_id: 'recording-1',
    seq_number: 0,
    timestamp_ns: 1000,
    channels: {
        // Video channel: keyframe timestamp is preferred over the log time.
        front: { channel_id: 1, log_time_ns: 2000, keyframe_log_time_ns: 1500 },
        // Non-video channel: falls back to the log time.
        rear: { channel_id: 2, log_time_ns: 3000, keyframe_log_time_ns: null }
        // `side` has no locator, so its tile is skipped.
    }
};

describe('CameraProjectionStrip', () => {
    const originalBaseUrl = client.getConfig().baseUrl;

    beforeAll(() => {
        client.setConfig({ baseUrl: TEST_BASE_URL });
    });

    afterAll(() => {
        client.setConfig({ baseUrl: originalBaseUrl });
    });

    beforeEach(() => {
        tickDetailsResult.data = undefined;
    });

    it('renders the strip chrome with its heading', () => {
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByTestId('workspace-projection-strip')).toBeInTheDocument();
        expect(screen.getByText('Cameras & projections')).toBeInTheDocument();
    });

    it('renders a frame only for channels that have a locator for the tick', () => {
        tickDetailsResult.data = tickDetails;
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toBeInTheDocument();
        expect(screen.getByRole('img', { name: 'rear' })).toBeInTheDocument();
        expect(screen.queryByRole('img', { name: 'side' })).not.toBeInTheDocument();
    });

    it('seeks video frames by keyframe timestamp and other frames by log time', () => {
        tickDetailsResult.data = tickDetails;
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toHaveAttribute(
            'src',
            `${TEST_BASE_URL}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=1&keyframe_timestamp_ns=1500`
        );
        expect(screen.getByRole('img', { name: 'rear' })).toHaveAttribute(
            'src',
            `${TEST_BASE_URL}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=2&keyframe_timestamp_ns=3000`
        );
    });

    it('renders no frames while the tick details are still loading', () => {
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByTestId('workspace-projection-strip')).toBeInTheDocument();
        expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });
});
