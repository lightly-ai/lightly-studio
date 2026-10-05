import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PerspectiveCamera, Vector3 } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { createSceneNavigationController } from './sceneNavigationController';
import { navigateScene } from './sceneNavigation';

describe('scene navigation controller', () => {
    let camera: PerspectiveCamera;
    let controls: { target: Vector3; enableDamping: boolean; update: ReturnType<typeof vi.fn> };
    let controller: ReturnType<typeof createSceneNavigationController>;

    beforeEach(() => {
        vi.useFakeTimers({
            toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame']
        });
        camera = new PerspectiveCamera();
        camera.position.set(10, 10, 10);
        controls = { target: new Vector3(), enableDamping: true, update: vi.fn() };
        controller = createSceneNavigationController({
            camera,
            controls: controls as unknown as OrbitControls,
            invalidate: vi.fn()
        });
    });

    afterEach(() => {
        controller.dispose();
        vi.useRealTimers();
    });

    it.each(['forward', 'backward', 'left', 'right', 'rotate-left', 'rotate-right'] as const)(
        'animates a %s step and stops',
        (action) => {
            const position = camera.position.clone();
            navigateScene(action);
            vi.advanceTimersByTime(192);
            expect(camera.position.equals(position)).toBe(false);
            expect(controls.enableDamping).toBe(true);
            expect(vi.getTimerCount()).toBe(0);
        }
    );

    it('cancels a step and removes the subscription on disposal', () => {
        navigateScene('left');
        vi.advanceTimersByTime(96);
        controller.cancel();
        expect(vi.getTimerCount()).toBe(0);
        expect(controls.enableDamping).toBe(true);
        controller.dispose();
        navigateScene('forward');
        expect(vi.getTimerCount()).toBe(0);
    });

    it('preserves initially disabled damping', () => {
        controls.enableDamping = false;
        navigateScene('right');
        vi.advanceTimersByTime(192);
        expect(controls.enableDamping).toBe(false);
    });
});
