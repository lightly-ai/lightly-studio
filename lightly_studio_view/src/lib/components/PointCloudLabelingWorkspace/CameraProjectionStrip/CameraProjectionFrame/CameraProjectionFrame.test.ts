import { render, screen } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/dom';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import CameraProjectionFrame from './CameraProjectionFrame.svelte';
import { DEFAULT_PROJECTION_SETTINGS } from '../projectionSettings';

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
    const context = {
        beginPath: vi.fn(),
        clearRect: vi.fn(),
        fillRect: vi.fn(),
        lineTo: vi.fn(),
        moveTo: vi.fn(),
        stroke: vi.fn(),
        fillStyle: '',
        lineWidth: 0,
        strokeStyle: ''
    };

    beforeAll(() => {
        client.setConfig({ baseUrl: TEST_BASE_URL });
    });

    beforeEach(() => {
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
            context as unknown as CanvasRenderingContext2D
        );
    });

    afterAll(() => {
        client.setConfig({ baseUrl: originalBaseUrl });
    });

    afterEach(() => {
        vi.restoreAllMocks();
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

    it('renders the projection overlay when projection metadata is available', () => {
        render(CameraProjectionFrame, {
            props: {
                ...defaultProps,
                projection: {
                    width: 640,
                    height: 480,
                    camera_matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
                    scene_to_camera: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
                },
                batch: {
                    positions: new Float32Array([0, 0, 1]),
                    intensities: new Float32Array([0]),
                    count: 1
                }
            }
        });

        const canvas = document.querySelector('canvas');
        expect(canvas).toBeInTheDocument();
        expect(canvas).toHaveProperty('width', 640);
        expect(canvas).toHaveProperty('height', 480);
        expect(context.fillRect).toHaveBeenCalledWith(-2, -2, 4, 4);
    });

    it('falls back to the placeholder when the frame image fails to load', async () => {
        render(CameraProjectionFrame, { props: defaultProps });
        await fireEvent.error(screen.getByRole('img', { name: 'front' }));

        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        expect(screen.getByText('front')).toBeInTheDocument();
    });

    it('shows the placeholder without an image', () => {
        const { unmount } = render(CameraProjectionFrame, {
            props: { ...defaultProps, blob: undefined }
        });
        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        unmount();
    });

    it('updates the enlarged frame while the dialog stays open', async () => {
        const { rerender } = render(CameraProjectionFrame, { props: defaultProps });

        await fireEvent.click(screen.getByRole('button', { name: 'Enlarge front' }));

        expect(screen.getByRole('dialog')).toBeInTheDocument();
        const enlargedImage = screen.getByRole('img', { name: 'front enlarged' });
        expect(enlargedImage).toHaveAttribute(
            'src',
            `${TEST_BASE_URL}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=3&keyframe_timestamp_ns=1500&log_time_ns=2000`
        );

        await rerender({ ...defaultProps, logTimeNs: '3000' });

        expect(screen.getByRole('img', { name: 'front enlarged' })).toHaveAttribute(
            'src',
            `${TEST_BASE_URL}/datasets/dataset-1/recordings/recording-1/camera-frame?channel_id=3&keyframe_timestamp_ns=1500&log_time_ns=3000`
        );
        expect(screen.getByRole('img', { name: 'front enlarged' })).toBe(enlargedImage);
        expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });

    it('uses Space for playback without closing the dialog', async () => {
        const onPlaybackToggle = vi.fn();
        render(CameraProjectionFrame, { props: { ...defaultProps, onPlaybackToggle } });

        await fireEvent.click(screen.getByRole('button', { name: 'Enlarge front' }));
        await fireEvent.keyDown(screen.getByRole('dialog'), { code: 'Space', key: ' ' });

        expect(onPlaybackToggle).toHaveBeenCalledOnce();
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('does not restore focus to the frame trigger when the dialog closes', async () => {
        render(CameraProjectionFrame, { props: defaultProps });

        const trigger = screen.getByRole('button', { name: 'Enlarge front' });
        await fireEvent.click(trigger);
        await fireEvent.click(screen.getByRole('button', { name: 'Close' }));

        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(document.activeElement).not.toBe(trigger);
    });

    it('does not trigger playback from a dialog control', async () => {
        const onPlaybackToggle = vi.fn();
        render(CameraProjectionFrame, {
            props: {
                ...defaultProps,
                onPlaybackToggle,
                projectionSettings: DEFAULT_PROJECTION_SETTINGS,
                onProjectionSettingsChange: vi.fn()
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Enlarge front' }));
        const settingsButton = screen.getByRole('button', { name: 'Projection settings' });
        await fireEvent.keyDown(settingsButton, { code: 'Space', key: ' ' });
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(onPlaybackToggle).toHaveBeenCalledOnce();
        expect(settingsButton).toHaveAttribute('aria-expanded', 'false');
        expect(document.activeElement).not.toBe(settingsButton);
    });

    it('shows projection settings in the expanded dialog', async () => {
        render(CameraProjectionFrame, {
            props: {
                ...defaultProps,
                projectionSettings: DEFAULT_PROJECTION_SETTINGS,
                onProjectionSettingsChange: vi.fn()
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Enlarge front' }));

        expect(screen.getByRole('button', { name: 'Projection settings' })).toBeInTheDocument();
    });
});
