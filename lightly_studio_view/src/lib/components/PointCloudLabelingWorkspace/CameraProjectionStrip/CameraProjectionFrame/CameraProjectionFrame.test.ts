import { render, screen } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CameraProjectionFrame from './CameraProjectionFrame.svelte';

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

    beforeEach(() => {
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
            context as unknown as CanvasRenderingContext2D
        );
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

    it('asks to enlarge the frame when the tile is clicked', async () => {
        const onEnlarge = vi.fn();
        render(CameraProjectionFrame, { props: { ...defaultProps, onEnlarge } });

        await fireEvent.click(screen.getByRole('button', { name: 'Enlarge front' }));

        expect(onEnlarge).toHaveBeenCalledOnce();
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
});
