import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { useTickCameraFrames } from '$lib/hooks/useTickData/useTickCameraFrames.svelte';
import CameraProjectionStrip from './CameraProjectionStrip.svelte';

// Mock the hooks' source modules so the barrel (`$lib/hooks`) re-exports the stubs and
// each test drives the query results without a live TanStack query.
const tickDetailsResult: { data: TickDetailView | undefined } = { data: undefined };
vi.mock('$lib/hooks/useTickDetails/useTickDetails', () => ({
    useTickDetails: () => ({ tickDetails: tickDetailsResult })
}));
const cameraFramesResult: { data: Record<number, Blob> | undefined } = { data: undefined };
vi.mock('$lib/hooks/useTickData/useTickCameraFrames.svelte', () => ({
    useTickCameraFrames: vi.fn(() => ({ query: cameraFramesResult }))
}));

const defaultProps = {
    datasetId: 'dataset-1',
    sequenceId: 'sequence-1',
    seqNumber: 0,
    cameraChannels: [
        { channel_id: 1, group_component_name: 'front', group_component_index: 0 },
        { channel_id: 2, group_component_name: 'rear', group_component_index: 1 }
    ],
    selectedChannelIds: [1, 2]
};

const tickDetails: TickDetailView = {
    sample_id: 'sample-1',
    collection_id: 'collection-1',
    recording_id: 'recording-1',
    seq_number: 0,
    timestamp_ns: 1000,
    camera_channels: {
        // Camera channel with a keyframe locator: renders, decoding from the keyframe.
        front: {
            channel_id: 1,
            group_component_name: 'front',
            log_time_ns: '2000',
            keyframe_log_time_ns: '1500'
        },
        // Camera channel with no keyframe locator, so its tile is skipped.
        rear: {
            channel_id: 2,
            group_component_name: 'rear',
            log_time_ns: '3000',
            keyframe_log_time_ns: null
        }
    },
    lidar_channels: {},
    annotations: [],
    tags: []
};

const frontImage = new Blob(['front'], { type: 'image/jpeg' });
const rearImage = new Blob(['rear'], { type: 'image/jpeg' });

describe('CameraProjectionStrip', () => {
    beforeEach(() => {
        tickDetailsResult.data = undefined;
        cameraFramesResult.data = undefined;
        // jsdom has no object URLs.
        URL.createObjectURL = vi.fn((blob: Blob) =>
            blob === frontImage ? 'blob:front' : 'blob:rear'
        );
        URL.revokeObjectURL = vi.fn();
    });

    it('keeps every selected summary channel visible when a tick has no frame', () => {
        tickDetailsResult.data = tickDetails;
        cameraFramesResult.data = { 1: frontImage };
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toBeInTheDocument();
        expect(screen.queryByRole('img', { name: 'rear' })).not.toBeInTheDocument();
        expect(screen.getByText('rear')).toBeInTheDocument();
    });

    it("shows each channel's image from the tick's data", () => {
        tickDetailsResult.data = tickDetails;
        cameraFramesResult.data = { 1: frontImage };
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toHaveAttribute('src', 'blob:front');
        const getParams = vi.mocked(useTickCameraFrames).mock.lastCall?.[0];
        expect(getParams?.()).toEqual({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 0,
            displayFrameId: undefined
        });
    });

    it('renders only the selected camera channels', () => {
        tickDetailsResult.data = {
            ...tickDetails,
            camera_channels: {
                ...tickDetails.camera_channels,
                rear: { ...tickDetails.camera_channels.rear, keyframe_log_time_ns: '2500' }
            }
        };
        cameraFramesResult.data = { 1: frontImage, 2: rearImage };
        render(CameraProjectionStrip, {
            props: { ...defaultProps, selectedChannelIds: [1] }
        });

        expect(screen.getByRole('img', { name: 'front' })).toBeInTheDocument();
        expect(screen.queryByRole('img', { name: 'rear' })).not.toBeInTheDocument();
    });

    it('renders no frames while the tick details are still loading', () => {
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByTestId('workspace-projection-strip')).toBeInTheDocument();
        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        expect(screen.getByText('front')).toBeInTheDocument();
        expect(screen.getByText('rear')).toBeInTheDocument();
    });
});
