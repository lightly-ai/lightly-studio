import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import CameraProjectionStrip from './CameraProjectionStrip.svelte';
import type { CameraFrame } from '../domain';

function camera(id: string, resourceId?: string): CameraFrame {
    return {
        id,
        source: { recordingId: 'r', streamId: '3', messageId: '1', publishedAt: null },
        timestamp: { nanoseconds: '1', clockId: 'log' },
        width: 480,
        height: 270,
        image: resourceId ? { kind: 'decoded', resourceId } : null,
        calibration: null
    };
}

describe('CameraProjectionStrip', () => {
    it('says so when the frame has no camera', () => {
        render(CameraProjectionStrip);

        expect(screen.getByText('No camera for this frame')).toBeInTheDocument();
        expect(screen.queryAllByTestId('workspace-camera-tile')).toHaveLength(0);
    });

    it('draws a tile per camera of the frame', () => {
        render(CameraProjectionStrip, {
            props: {
                cameras: [camera('/camera_front', 'a'), camera('/camera_rear', 'b')],
                resolveImage: () => undefined
            }
        });

        expect(screen.getAllByTestId('workspace-camera-tile')).toHaveLength(2);
        expect(screen.getByText('/camera_front')).toBeInTheDocument();
    });

    it('asks for the picture each camera refers to', () => {
        const resolveImage = vi.fn(() => undefined);

        render(CameraProjectionStrip, {
            props: { cameras: [camera('/camera_front', 'cam:42')], resolveImage }
        });

        expect(resolveImage).toHaveBeenCalledWith('cam:42');
    });

    it('still shows a camera that published no picture for this frame', () => {
        render(CameraProjectionStrip, { props: { cameras: [camera('/camera_front')] } });

        expect(screen.getByTestId('workspace-camera-tile')).toBeInTheDocument();
        expect(screen.getByText('/camera_front')).toBeInTheDocument();
    });

    it('keeps the orthographic projections alongside the cameras', () => {
        render(CameraProjectionStrip, { props: { cameras: [camera('/camera_front', 'a')] } });

        expect(screen.getByText('Top (BEV)')).toBeInTheDocument();
    });
});
