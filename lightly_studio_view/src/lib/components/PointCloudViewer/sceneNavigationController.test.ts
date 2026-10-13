import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PerspectiveCamera, Vector3 } from 'three';
import { createSceneNavigationController } from './sceneNavigationController';
import { navigateScene, startSceneNavigation, stopSceneNavigation } from './sceneNavigation';

describe('scene navigation controller', () => {
    let frames: Map<number, FrameRequestCallback>;
    let frameId: number;
    let now: number;
    let camera: PerspectiveCamera;
    let controls: { target: Vector3; enableDamping: boolean; update: ReturnType<typeof vi.fn> };
    let controller: ReturnType<typeof createSceneNavigationController>;

    function advance(milliseconds: number) {
        now += milliseconds;
        const pending = [...frames.values()];
        frames.clear();
        for (const callback of pending) callback(now);
    }

    beforeEach(() => {
        frames = new Map();
        frameId = 0;
        now = 0;
        vi.spyOn(performance, 'now').mockImplementation(() => now);
        vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
            frames.set(++frameId, callback);
            return frameId;
        });
        vi.stubGlobal('cancelAnimationFrame', (id: number) => frames.delete(id));
        camera = new PerspectiveCamera();
        camera.position.set(10, 10, 10);
        controls = { target: new Vector3(), enableDamping: true, update: vi.fn() };
        controller = createSceneNavigationController({
            camera,
            controls: controls as never,
            invalidate: vi.fn()
        });
    });

    afterEach(() => {
        controller.dispose();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('moves until both keyboard and pointer holds release the same action', () => {
        startSceneNavigation('forward');
        startSceneNavigation('forward');
        advance(20);
        stopSceneNavigation('forward');
        const position = camera.position.clone();
        advance(20);
        expect(camera.position.equals(position)).toBe(false);
        stopSceneNavigation('forward');
        const stopped = camera.position.clone();
        advance(20);
        expect(camera.position.equals(stopped)).toBe(true);
        expect(controls.enableDamping).toBe(true);
        expect(frames.size).toBe(0);
    });

    it('resumes held movement after a discrete navigation step finishes', () => {
        startSceneNavigation('forward');
        advance(20);
        navigateScene('right');
        advance(90);
        expect(controls.enableDamping).toBe(false);
        advance(90);
        const position = camera.position.clone();
        advance(20);
        expect(camera.position.equals(position)).toBe(false);
        stopSceneNavigation('forward');
        advance(20);
        expect(controls.enableDamping).toBe(true);
    });

    it('restores damping if the held input releases during a step', () => {
        startSceneNavigation('forward');
        navigateScene('rotate-left');
        stopSceneNavigation('forward');
        advance(180);
        expect(controls.enableDamping).toBe(true);
        expect(frames.size).toBe(0);
    });

    it.each(['forward', 'backward', 'left', 'right', 'rotate-left', 'rotate-right'] as const)(
        'animates a %s step and stops',
        (action) => {
            const position = camera.position.clone();
            navigateScene(action);
            advance(180);
            expect(camera.position.equals(position)).toBe(false);
            expect(controls.enableDamping).toBe(true);
            expect(frames.size).toBe(0);
        }
    );

    it('cancels all held actions and removes the subscription on disposal', () => {
        startSceneNavigation('left');
        startSceneNavigation('rotate-right');
        advance(20);
        controller.cancel();
        expect(frames.size).toBe(0);
        expect(controls.enableDamping).toBe(true);
        controller.dispose();
        navigateScene('forward');
        expect(frames.size).toBe(0);
    });

    it('preserves initially disabled damping', () => {
        controls.enableDamping = false;
        startSceneNavigation('right');
        stopSceneNavigation('right');
        advance(20);
        expect(controls.enableDamping).toBe(false);
    });
});
