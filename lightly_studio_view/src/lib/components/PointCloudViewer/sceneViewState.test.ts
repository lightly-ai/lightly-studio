import { describe, expect, it } from 'vitest';
import { OrthographicCamera, PerspectiveCamera, Vector3 } from 'three';
import { applyCameraViewState, getCameraWorldUnitsPerPixel } from './sceneViewState';

describe('shared camera scale', () => {
    it('keeps the same projected world length when an orthographic viewport expands and restores', () => {
        const camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 1000);
        camera.position.set(0, 0, 20);
        camera.lookAt(0, 0, 0);
        const target = new Vector3();
        const state = { target: [0, 0, 0] as const, worldUnitsPerPixel: 0.025 };
        for (const viewport of [
            { width: 600, height: 240 },
            { width: 1800, height: 720 },
            { width: 600, height: 240 }
        ]) {
            applyCameraViewState(camera, target, state, viewport);
            camera.updateMatrixWorld();
            const left = new Vector3(-1, 0, 0).project(camera);
            const right = new Vector3(1, 0, 0).project(camera);
            expect(((right.x - left.x) * viewport.width) / 2).toBeCloseTo(80);
            expect(getCameraWorldUnitsPerPixel(camera, target, viewport.height)).toBeCloseTo(0.025);
        }
    });

    it('synchronizes zoom and position bidirectionally between perspective and orthographic cameras', () => {
        const main = new PerspectiveCamera(60, 2, 0.1, 1000);
        main.zoom = 1.5;
        main.position.set(0, -20, 0);
        const mainTarget = new Vector3();
        const scale = getCameraWorldUnitsPerPixel(main, mainTarget, 400)!;
        const top = new OrthographicCamera(-1, 1, 1, -1);
        top.position.set(0, 0, 20);
        const topTarget = new Vector3();
        const viewport = { width: 500, height: 200 };
        applyCameraViewState(
            top,
            topTarget,
            {
                target: [0, 0, 0],
                worldUnitsPerPixel: scale
            },
            viewport
        );
        expect(getCameraWorldUnitsPerPixel(top, topTarget, 200)).toBeCloseTo(scale);

        top.zoom *= 2;
        topTarget.set(3, 4, 0);
        const nextScale = getCameraWorldUnitsPerPixel(top, topTarget, 200)!;
        applyCameraViewState(
            main,
            mainTarget,
            {
                target: [3, 4, 0],
                worldUnitsPerPixel: nextScale
            },
            { width: 800, height: 400 }
        );
        expect(mainTarget.toArray()).toEqual([3, 4, 0]);
        expect(main.position.clone().sub(mainTarget).toArray()).toEqual([0, -10, 0]);
        expect(getCameraWorldUnitsPerPixel(main, mainTarget, 400)).toBeCloseTo(nextScale);
    });

    it('uses the actual orthographic frustum span and ignores hidden viewport sizes', () => {
        const camera = new OrthographicCamera(-4, 4, 2, -2);
        camera.zoom = 2;
        const target = new Vector3();
        expect(getCameraWorldUnitsPerPixel(camera, target, 200)).toBeCloseTo(0.01);
        expect(getCameraWorldUnitsPerPixel(camera, target, 0)).toBeUndefined();
        expect(
            applyCameraViewState(
                camera,
                target,
                {
                    target: [1, 2, 3],
                    worldUnitsPerPixel: 0.02
                },
                { width: 0, height: 0 }
            )
        ).toBe(false);
        expect(camera.zoom).toBe(2);
        expect(target.toArray()).toEqual([0, 0, 0]);
    });
});
