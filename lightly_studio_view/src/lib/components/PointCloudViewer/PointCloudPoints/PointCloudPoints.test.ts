import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { PerspectiveCamera, Vector3 } from 'three';
import PointCloudPoints from './PointCloudPoints.svelte';

const { buffer, invalidate, fitCamera } = vi.hoisted(() => ({
    buffer: {
        geometry: {},
        updatePositions: vi.fn(),
        updateColors: vi.fn(),
        dispose: vi.fn()
    },
    invalidate: vi.fn(),
    fitCamera: vi.fn()
}));

vi.mock('@threlte/core', async () => {
    const Points = (await import('./PointsStub.svelte')).default;
    return { T: { Points, PointsMaterial: Points }, useThrelte: () => ({ invalidate }) };
});
vi.mock('../pointCloudBuffer', () => ({ createPointCloudBuffer: () => buffer }));
vi.mock('../pointCloudCamera', () => ({ fitCameraToBounds: fitCamera }));

const defaultProps: ComponentProps<typeof PointCloudPoints> = {
    batch: { positions: new Float32Array([1, 2, 3]), intensities: new Float32Array([1]), count: 1 },
    colorMode: 'none',
    pointSize: 2
};
const bounds = { min: new Vector3(1, 2, 3), max: new Vector3(1, 2, 3) };

beforeEach(() => {
    vi.clearAllMocks();
    buffer.updatePositions.mockReturnValue(bounds);
});

describe('PointCloudPoints', () => {
    it('waits for bounds and both camera refs before fitting, then preserves the view', async () => {
        const { rerender } = render(PointCloudPoints, { props: defaultProps });
        expect(fitCamera).not.toHaveBeenCalled();
        const camera = new PerspectiveCamera();
        await rerender({ camera });
        expect(fitCamera).not.toHaveBeenCalled();
        buffer.updatePositions.mockReturnValue(undefined);
        const controls = { target: new Vector3() } as NonNullable<
            ComponentProps<typeof PointCloudPoints>['controls']
        >;
        await rerender({ controls });
        expect(fitCamera).not.toHaveBeenCalled();
        buffer.updatePositions.mockReturnValue(bounds);
        const batch = { ...defaultProps.batch, positions: new Float32Array([4, 5, 6]) };
        await rerender({ batch });
        expect(fitCamera).toHaveBeenCalledExactlyOnceWith(camera, controls, bounds);
        await rerender({ batch: defaultProps.batch, camera: new PerspectiveCamera() });
        expect(fitCamera).toHaveBeenCalledTimes(1);
    });

    it('updates positions and colors when the batch or color settings change', async () => {
        const { rerender } = render(PointCloudPoints, { props: defaultProps });
        vi.clearAllMocks();
        const colors = new Float32Array([0.1, 0.2, 0.3]);
        const batch = { ...defaultProps.batch, colors };
        await rerender({ batch });
        expect(buffer.updatePositions).toHaveBeenCalledWith(batch);
        expect(buffer.updateColors).toHaveBeenCalledWith(1, 'none', undefined, colors);
        expect(invalidate).toHaveBeenCalled();
        vi.clearAllMocks();
        await rerender({ batch, colorMode: 'intensity', intensityRange: [0, 10] });
        expect(buffer.updateColors).toHaveBeenCalledExactlyOnceWith(
            1,
            'intensity',
            [0, 10],
            colors
        );
        expect(invalidate).toHaveBeenCalled();
    });

    it('keeps buffers alive through updates and disposes them on unmount', async () => {
        const { rerender, unmount } = render(PointCloudPoints, { props: defaultProps });
        await rerender({ pointSize: 4 });
        expect(buffer.dispose).not.toHaveBeenCalled();
        unmount();
        expect(buffer.dispose).toHaveBeenCalledOnce();
    });
});
