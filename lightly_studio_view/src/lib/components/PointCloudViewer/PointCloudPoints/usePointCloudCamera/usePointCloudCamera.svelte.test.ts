import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Box3, OrthographicCamera, PerspectiveCamera, Vector3 } from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { usePointCloudCamera } from './usePointCloudCamera.svelte';
import { getCameraWorldUnitsPerPixel } from '../../sceneViewState';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';

const threlte = vi.hoisted(() => ({
    renderer: { domElement: undefined as unknown as HTMLCanvasElement },
    invalidate: vi.fn()
}));
vi.mock('@threlte/core', () => ({ useThrelte: () => threlte }));

type Options = ReturnType<Parameters<typeof usePointCloudCamera>[0]>;
const bounds = new Box3(new Vector3(-5, -5, -2), new Vector3(5, 5, 2));
const cleanups: (() => void)[] = [];

function setup(overrides: Partial<Options> = {}, width = 600, height = 240) {
    const viewport = { width, height };
    const canvas = document.createElement('canvas');
    Object.defineProperties(canvas, {
        clientWidth: { get: () => viewport.width },
        clientHeight: { get: () => viewport.height }
    });
    threlte.renderer.domElement = canvas;
    const camera = overrides.camera ?? new PerspectiveCamera(60, 2.5, 0.1, 10000);
    camera.up.set(
        0,
        overrides.cameraMode === 'top' ? 1 : 0,
        overrides.cameraMode === 'top' ? 0 : 1
    );
    const controls = new OrbitControls(camera, canvas);
    const options = $state<Options>({
        camera,
        controls,
        fitKey: 'sequence/map',
        isScaleSource: true,
        onViewStateChange: vi.fn(),
        ...overrides
    });
    let resize = () => {};
    const disconnect = vi.fn();
    vi.stubGlobal(
        'ResizeObserver',
        class {
            constructor(callback: () => void) {
                resize = callback;
            }
            observe = vi.fn();
            disconnect = disconnect;
        }
    );
    let sync!: ReturnType<typeof usePointCloudCamera>;
    const dispose = $effect.root(() => {
        sync = usePointCloudCamera(() => options);
        sync.updateBounds(bounds);
    });
    cleanups.push(() => {
        dispose();
        controls.dispose();
    });
    flushSync();
    return {
        options,
        camera,
        controls,
        sync,
        viewport,
        resize: () => resize(),
        dispose,
        disconnect
    };
}

afterEach(() => {
    cleanups.splice(0).forEach((cleanup) => cleanup());
    vi.unstubAllGlobals();
    vi.clearAllMocks();
});

describe('camera synchronization lifecycle', () => {
    it('waits for the first usable viewport size before publishing the initial scale', () => {
        const { options, camera, controls, viewport, resize } = setup({}, 0, 0);
        expect(options.onViewStateChange).not.toHaveBeenCalled();
        viewport.width = 800;
        viewport.height = 400;
        resize();

        expect(options.onViewStateChange).toHaveBeenCalledOnce();
        expect(options.onViewStateChange).toHaveBeenCalledWith({
            target: controls.target.toArray(),
            worldUnitsPerPixel: getCameraWorldUnitsPerPixel(camera, controls.target, 400)
        });
    });

    it.each(['top', 'side', 'front'] as const)(
        'applies shared scale on the first visible %s render and preserves it through expansion',
        (cameraMode) => {
            const camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 10000);
            const { viewport, controls, resize, options } = setup(
                {
                    camera,
                    cameraMode,
                    isScaleSource: false,
                    viewState: { target: [1, 2, 3], worldUnitsPerPixel: 0.04 }
                },
                0,
                0
            );
            for (const [width, height] of [
                [600, 240],
                [1800, 720],
                [600, 240]
            ]) {
                Object.assign(viewport, { width, height });
                resize();
                camera.updateMatrixWorld();
                const start = controls.target.clone().project(camera);
                const axis = cameraMode === 'side' ? new Vector3(0, 1, 0) : new Vector3(1, 0, 0);
                const end = controls.target.clone().add(axis).project(camera);
                expect((Math.abs(end.x - start.x) * width) / 2).toBeCloseTo(25);
                expect(controls.target.toArray()).toEqual([1, 2, 3]);
            }
            // Applying shared state must not feed another change back into sibling cameras.
            expect(options.onViewStateChange).not.toHaveBeenCalled();
        }
    );

    it('publishes user zoom and pan from a follower without feeding back applied changes', () => {
        const camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 10000);
        const { options, controls } = setup({
            camera,
            cameraMode: 'top',
            isScaleSource: false,
            viewState: { target: [0, 0, 0], worldUnitsPerPixel: 0.04 }
        });
        expect(options.onViewStateChange).not.toHaveBeenCalled();
        camera.zoom *= 2;
        controls.target.set(3, 4, 0);
        controls.update();
        expect(options.onViewStateChange).toHaveBeenLastCalledWith({
            target: [expect.closeTo(3), expect.closeTo(4), expect.closeTo(0)],
            worldUnitsPerPixel: 0.02
        });
        vi.mocked(options.onViewStateChange!).mockClear();

        options.viewState = { target: [5, 6, 0], worldUnitsPerPixel: 0.01 };
        flushSync();
        expect(getCameraWorldUnitsPerPixel(camera, controls.target, 240)).toBeCloseTo(0.01);
        expect(controls.target.toArray()).toEqual([
            expect.closeTo(5),
            expect.closeTo(6),
            expect.closeTo(0)
        ]);
        expect(options.onViewStateChange).not.toHaveBeenCalled();
    });

    it('preserves navigation across playback frames but refits after a coordinate-frame change', () => {
        const { camera, controls, sync, options } = setup();
        camera.position.multiplyScalar(0.5);
        controls.update();
        const position = camera.position.clone();
        const nextBounds = new Box3(new Vector3(90, 90, 0), new Vector3(110, 110, 4));
        sync.updateBounds(nextBounds);
        expect(camera.position.toArray()).toEqual(position.toArray());

        options.fitKey = 'sequence/sensor';
        flushSync();
        sync.updateBounds(nextBounds);
        expect(controls.target.toArray()).toEqual([100, 100, 2]);
        expect(camera.position.toArray()).not.toEqual(position.toArray());
    });

    it('disconnects resize and control listeners when the viewport is destroyed', () => {
        const { controls, options, dispose, disconnect } = setup();
        vi.mocked(options.onViewStateChange!).mockClear();
        dispose();
        controls.dispatchEvent({ type: 'change' });
        expect(options.onViewStateChange).not.toHaveBeenCalled();
        expect(disconnect).toHaveBeenCalledOnce();
    });
});

describe('independent object cameras', () => {
    it.each(['top', 'front', 'side'] as const)(
        'keeps the %s camera fixed through resize snapshots and commits',
        (cameraMode) => {
            const cuboid = createAnnotationFixture();
            const camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 10000);
            const { options, controls, resize } = setup({
                camera,
                cameraMode,
                cameraCuboid: cuboid,
                isScaleSource: false
            });
            camera.zoom *= 2;
            const pan = new Vector3(0.25, 0.5, 0.75);
            camera.position.add(pan);
            controls.target.add(pan);
            controls.update();
            const position = camera.position.clone();
            const orientation = camera.quaternion.clone();
            const target = controls.target.clone();
            const zoom = camera.zoom;
            for (const annotation of [
                { ...cuboid },
                { ...cuboid, center: [11, -2, 1] as const, size: [6, 2, 2] as const }
            ]) {
                options.cameraCuboid = annotation;
                flushSync();
                resize();
                expect(camera.position.distanceTo(position)).toBeCloseTo(0);
                expect(camera.quaternion.angleTo(orientation)).toBeCloseTo(0);
                expect(controls.target.distanceTo(target)).toBeCloseTo(0);
                expect(camera.zoom).toBeCloseTo(zoom);
            }
        }
    );

    it('follows cuboid selection and rotation while keeping navigation local', () => {
        const cuboid = createAnnotationFixture();
        const camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 10000);
        const { options, controls, viewport, resize } = setup({
            camera,
            cameraMode: 'front',
            cameraCuboid: cuboid,
            isScaleSource: false
        });
        expect(controls.target.distanceTo(new Vector3(...cuboid.center))).toBeCloseTo(0);
        expect(camera.getWorldDirection(new Vector3()).x).toBeCloseTo(-1);
        camera.zoom *= 2;
        controls.target.add(new Vector3(0, 1, 0));
        controls.update();
        expect(options.onViewStateChange).not.toHaveBeenCalled();
        const zoom = camera.zoom;
        viewport.width *= 2;
        resize();
        expect(camera.zoom).toBeCloseTo(zoom);
        expect(camera.right).toBeCloseTo(viewport.width / viewport.height);
        viewport.width = 0;
        options.cameraCuboid = {
            ...cuboid,
            center: [20, 5, 3],
            rotation: [0, 0, Math.SQRT1_2, Math.SQRT1_2]
        };
        flushSync();
        viewport.width = 600;
        resize();
        expect(controls.target.distanceTo(new Vector3(20, 5, 3))).toBeCloseTo(0);
        expect(camera.getWorldDirection(new Vector3()).y).toBeCloseTo(-1);
        expect(options.onViewStateChange).not.toHaveBeenCalled();
    });
});
