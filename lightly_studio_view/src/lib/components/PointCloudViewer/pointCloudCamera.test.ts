import { describe, expect, it, vi } from 'vitest';
import { Box3, PerspectiveCamera, Vector3 } from 'three';
import { fitCameraToBounds } from './pointCloudCamera';

describe('fitCameraToBounds', () => {
    it('does nothing when camera is undefined', () => {
        expect(() => fitCameraToBounds(undefined, undefined, new Box3())).not.toThrow();
    });

    it('positions camera from bounds', () => {
        const camera = new PerspectiveCamera();
        const bounds = new Box3(new Vector3(0, 0, 0), new Vector3(20, 0, 0));

        fitCameraToBounds(camera, undefined, bounds);

        expect(camera.position.toArray()).toEqual([40, -30, 19.5]);
    });

    it('calls lookAt on camera when controls are absent', () => {
        const camera = new PerspectiveCamera();
        const lookAt = vi.spyOn(camera, 'lookAt');

        fitCameraToBounds(camera, undefined, new Box3());

        expect(lookAt).toHaveBeenCalledWith(0, 0, 0);
    });

    it('sets orbit target from bounds when controls are present', () => {
        const camera = new PerspectiveCamera();
        const controls = { enableDamping: false, target: new Vector3(), update: vi.fn() };
        const bounds = new Box3(new Vector3(0, 0, 0), new Vector3(20, 0, 0));

        fitCameraToBounds(camera, controls as never, bounds);

        expect(controls.target.toArray()).toEqual([10, 0, 0]);
    });

    it('calls controls.update when controls are present', () => {
        const camera = new PerspectiveCamera();
        const controls = { enableDamping: false, target: new Vector3(), update: vi.fn() };

        fitCameraToBounds(camera, controls as never, new Box3());

        expect(controls.update).toHaveBeenCalledOnce();
    });

    it('disables damping during update and restores the original value', () => {
        const camera = new PerspectiveCamera();
        const controls = { enableDamping: true, target: new Vector3(), update: vi.fn() };
        let dampingDuringUpdate: boolean | undefined;
        controls.update = vi.fn(() => {
            dampingDuringUpdate = controls.enableDamping;
        });

        fitCameraToBounds(camera, controls as never, new Box3());

        expect(dampingDuringUpdate).toBe(false);
        expect(controls.enableDamping).toBe(true);
    });

    it('preserves enableDamping false when controls start with damping disabled', () => {
        const camera = new PerspectiveCamera();
        const controls = { enableDamping: false, target: new Vector3(), update: vi.fn() };
        let dampingDuringUpdate: boolean | undefined;
        controls.update = vi.fn(() => {
            dampingDuringUpdate = controls.enableDamping;
        });

        fitCameraToBounds(camera, controls as never, new Box3());

        expect(dampingDuringUpdate).toBe(false);
        expect(controls.enableDamping).toBe(false);
        expect(controls.update).toHaveBeenCalledOnce();
    });
});
