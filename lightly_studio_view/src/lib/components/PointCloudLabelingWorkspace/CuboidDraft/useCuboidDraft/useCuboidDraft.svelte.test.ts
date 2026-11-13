import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { OrthographicCamera, PerspectiveCamera, type Camera } from 'three';
import { render } from '@testing-library/svelte';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CameraMode } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { useCuboidDraft } from './useCuboidDraft.svelte';
import CuboidDraftHarness from './CuboidDraftHarness.svelte';

const mocks = vi.hoisted(() => ({ useThrelte: vi.fn() }));
vi.mock('@threlte/core', () => ({ useThrelte: mocks.useThrelte }));

type Draft = ReturnType<typeof useCuboidDraft>;

let cleanup: () => void;
let canvas: HTMLCanvasElement;
const onCreate = vi.fn();

beforeEach(() => {
    vi.clearAllMocks();
    canvas = document.createElement('canvas');
    canvas.getBoundingClientRect = () => new DOMRect(0, 0, 400, 400);
    canvas.setPointerCapture = vi.fn();
    canvas.hasPointerCapture = () => true;
    canvas.releasePointerCapture = vi.fn();
});
afterEach(() => cleanup?.());

/** Looks down −Z; spans [-4, 4] on x and y over 400 px: 50 px per meter, pixel (200, 200) is the origin. */
function createTopCamera(): Camera {
    const camera = new OrthographicCamera(-4, 4, 4, -4, 0.1, 100);
    camera.position.set(0, 0, 10);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    return camera;
}

/** Looks along −X; pixel (200, 200) is y = 0, z = 0, with y to the right and z up, 50 px per meter. */
function createSideCamera(): Camera {
    const camera = new OrthographicCamera(-4, 4, 4, -4, 0.1, 100);
    camera.up.set(0, 0, 1);
    camera.position.set(10, 0, 0);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    return camera;
}

/** Looks straight down from z = 10; pixel (200, 200) is the origin, 20 px per meter on the ground. */
function createDownCamera(): Camera {
    const camera = new PerspectiveCamera(90, 1, 0.1, 100);
    camera.position.set(0, 0, 10);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    return camera;
}

/** Looks along +Y at height 1; pixels above the vertical center point above the horizon. */
function createHorizontalCamera(): Camera {
    const camera = new PerspectiveCamera(90, 1, 0.1, 100);
    camera.up.set(0, 0, 1);
    camera.position.set(0, -10, 1);
    camera.lookAt(0, 0, 1);
    camera.updateMatrixWorld();
    return camera;
}

function createBatch(points: number[][]): PointBatch {
    return {
        positions: new Float32Array(points.flat()),
        intensities: new Float32Array(points.length),
        count: points.length
    };
}

function pointer(type: string, clientX: number, clientY: number, button = 0, pointerId = 7) {
    const event = new MouseEvent(type, {
        clientX,
        clientY,
        button,
        buttons: 1,
        cancelable: true
    });
    Object.defineProperty(event, 'pointerId', { value: pointerId });
    return event as PointerEvent;
}

interface SetupOptions {
    cameraMode?: CameraMode;
    camera?: Camera;
    batch?: PointBatch;
}

function setup({
    cameraMode = 'perspective',
    camera = createTopCamera(),
    batch
}: SetupOptions = {}) {
    mocks.useThrelte.mockReturnValue({
        camera: { current: camera },
        renderer: { domElement: canvas }
    });
    const ref: { current?: Draft } = {};
    const instance = render(CuboidDraftHarness, {
        props: {
            getCameraMode: () => cameraMode,
            getBatch: () => batch,
            getTick: () => 0,
            onCreate,
            onReady: (draft: Draft) => {
                ref.current = draft;
            }
        }
    });
    cleanup = () => {
        instance.unmount();
        cleanup = () => {};
    };
    return { draft: ref.current!, rerender: instance.rerender };
}

function pressAt(
    draft: Draft,
    clientX: number,
    clientY: number,
    point: [number, number, number],
    button = 0
) {
    const [x, y, z] = point;
    draft.handlePlanePointerDown({
        point: { x, y, z },
        nativeEvent: pointer('pointerdown', clientX, clientY, button)
    });
}

/** Presses at world (0, 0, 0) in the top view and drags the first side to world (2, 0, 0). */
function dragSide(draft: Draft) {
    pressAt(draft, 200, 200, [0, 0, 0]);
    canvas.dispatchEvent(pointer('pointermove', 300, 200));
}

/** Draws the side from (0, 0) to (2, 0), releases, and moves to a width of 1 toward +Y. */
function drawSideAndWidth(draft: Draft) {
    dragSide(draft);
    canvas.dispatchEvent(pointer('pointerup', 300, 200));
    canvas.dispatchEvent(pointer('pointermove', 300, 150));
}

function click(clientX: number, clientY: number, button = 0) {
    const event = pointer('pointerdown', clientX, clientY, button);
    canvas.dispatchEvent(event);
    return event;
}

/**
 * Draws a footprint with the horizontal camera in the 3D view: the side from world (0, -8, 0) to
 * (2, -6, 0), then a width click at world (-2, -6, 0). The height step follows.
 */
function startHeightStep() {
    const { draft } = setup({ cameraMode: 'perspective', camera: createHorizontalCamera() });
    pressAt(draft, 200, 300, [0, -8, 0]);
    canvas.dispatchEvent(pointer('pointermove', 300, 250));
    canvas.dispatchEvent(pointer('pointerup', 300, 250));
    canvas.dispatchEvent(pointer('pointermove', 100, 250));
    click(100, 250);
    return draft;
}

describe('useCuboidDraft', () => {
    describe('side and front views', () => {
        it('creates a fitted box after one drag', () => {
            const batch = createBatch([
                [3, 1, 0.5],
                [5, 1, 0.5],
                [9, 3, 0.5]
            ]);
            const { draft } = setup({ cameraMode: 'side', camera: createSideCamera(), batch });
            pressAt(draft, 200, 200, [0, 0, 0]);
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            canvas.dispatchEvent(pointer('pointerup', 300, 150));
            expect(onCreate).toHaveBeenCalledOnce();
            const box = onCreate.mock.calls[0][0];
            expect(box.center).toEqual([4, expect.closeTo(1), expect.closeTo(0.5)]);
            expect(box.size).toEqual([2, expect.closeTo(2), expect.closeTo(1)]);
            expect(box.yaw).toBe(0);
        });

        it('highlights the points along the whole depth of the rectangle', () => {
            const { draft } = setup({ cameraMode: 'side', camera: createSideCamera() });
            pressAt(draft, 200, 200, [0, 0, 0]);
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            expect(draft.highlightBox?.size).toEqual([
                Infinity,
                expect.closeTo(2),
                expect.closeTo(1)
            ]);
        });

        it('creates nothing on a click without a drag', () => {
            const { draft } = setup({ cameraMode: 'side', camera: createSideCamera() });
            pressAt(draft, 200, 200, [0, 0, 0]);
            canvas.dispatchEvent(pointer('pointerup', 201, 201));
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            expect(onCreate).not.toHaveBeenCalled();
            expect(draft.previewBox).toBeNull();
        });
    });

    describe('top view', () => {
        it('creates a fitted box after one drag', () => {
            const { draft } = setup({ cameraMode: 'top' });
            pressAt(draft, 200, 200, [0, 0, 0]);
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            canvas.dispatchEvent(pointer('pointerup', 300, 150));
            expect(onCreate).toHaveBeenCalledOnce();
            const box = onCreate.mock.calls[0][0];
            expect(box.size).toEqual([expect.closeTo(2), expect.closeTo(1), expect.closeTo(1)]);
            expect(box.yaw).toBe(0);
        });
    });

    describe('angled footprint', () => {
        it('previews the side as a thin box and keeps it after the release', () => {
            const { draft } = setup();
            dragSide(draft);
            canvas.dispatchEvent(pointer('pointerup', 300, 200));
            expect(onCreate).not.toHaveBeenCalled();
            expect(draft.previewBox?.size).toEqual([expect.closeTo(2), 0.1, 0.1]);
            expect(draft.previewBox?.yaw).toBeCloseTo(0);
        });

        it('highlights no points for the side and a column of points for the width', () => {
            const { draft } = setup();
            dragSide(draft);
            expect(draft.highlightBox).toBeNull();
            canvas.dispatchEvent(pointer('pointerup', 300, 200));
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            expect(draft.highlightBox?.size).toEqual([
                expect.closeTo(2),
                expect.closeTo(1),
                Infinity
            ]);
        });

        it('creates an angled box fitted to the points after the width click', () => {
            const batch = createBatch([
                [0, 1, 0.25],
                [0, 1, 1.75],
                [3, 3, 9]
            ]);
            const { draft } = setup({ batch });
            // Side from (0, 0) to (1, 1); the width point (0, 2) is √2 to the left of it.
            pressAt(draft, 200, 200, [0, 0, 0]);
            canvas.dispatchEvent(pointer('pointermove', 250, 150));
            canvas.dispatchEvent(pointer('pointerup', 250, 150));
            canvas.dispatchEvent(pointer('pointermove', 200, 100));
            click(200, 100);
            click(200, 100);
            expect(onCreate).toHaveBeenCalledOnce();
            const box = onCreate.mock.calls[0][0];
            expect(box.yaw).toBeCloseTo(Math.PI / 4);
            expect(box.center).toEqual([expect.closeTo(0), expect.closeTo(1), expect.closeTo(1)]);
            expect(box.size).toEqual([
                expect.closeTo(Math.SQRT2),
                expect.closeTo(Math.SQRT2),
                expect.closeTo(1.5)
            ]);
            expect(draft.previewBox).toBeNull();
        });

        it('sets the end of the side with a second click after a press without a drag', () => {
            const { draft } = setup();
            pressAt(draft, 200, 200, [0, 0, 0]);
            canvas.dispatchEvent(pointer('pointerup', 200, 200));
            expect(draft.previewBox).toBeNull();
            canvas.dispatchEvent(pointer('pointermove', 300, 200));
            expect(draft.previewBox?.size[0]).toBeCloseTo(2);
            click(300, 200);
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            click(300, 150);
            click(300, 150);
            expect(onCreate).toHaveBeenCalledOnce();
            expect(onCreate.mock.calls[0][0].size.slice(0, 2)).toEqual([
                expect.closeTo(2),
                expect.closeTo(1)
            ]);
        });

        it('does not start a new draft from the click that ends the draft', () => {
            const { draft } = setup();
            drawSideAndWidth(draft);
            click(300, 150);
            const nativeEvent = click(300, 150);
            draft.handlePlanePointerDown({ point: { x: 2, y: 1, z: 0 }, nativeEvent });
            canvas.dispatchEvent(pointer('pointermove', 350, 100));
            expect(onCreate).toHaveBeenCalledOnce();
            expect(draft.previewBox).toBeNull();
        });

        it.each(['Escape', 'contextmenu', 'right click'])(
            'discards the draft in the width step on %s',
            (reason) => {
                const { draft } = setup();
                drawSideAndWidth(draft);
                if (reason === 'Escape')
                    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                else if (reason === 'right click') click(300, 150, 2);
                else canvas.dispatchEvent(pointer(reason, 300, 150));
                expect(draft.previewBox).toBeNull();
                click(300, 150);
                expect(onCreate).not.toHaveBeenCalled();
            }
        );

        it.each(['shiftKey', 'ctrlKey', 'metaKey'])(
            'does not confirm the width with a %s click',
            (modifier) => {
                const { draft } = setup();
                drawSideAndWidth(draft);
                const event = pointer('pointerdown', 300, 150);
                Object.defineProperty(event, modifier, { value: true });
                canvas.dispatchEvent(event);
                expect(onCreate).not.toHaveBeenCalled();
                expect(draft.previewBox).not.toBeNull();
            }
        );

        it('keeps the draft when the pointer capture ends with the release', () => {
            const { draft } = setup();
            drawSideAndWidth(draft);
            canvas.dispatchEvent(pointer('lostpointercapture', 300, 150));
            expect(draft.previewBox).not.toBeNull();
        });
    });

    describe('3D view', () => {
        it('asks for the height after the width click', () => {
            const draft = startHeightStep();
            expect(onCreate).not.toHaveBeenCalled();
            expect(draft.previewBox?.size[2]).toBeCloseTo(0.1);
        });

        it('highlights the points up to the height in the height step', () => {
            const draft = startHeightStep();
            canvas.dispatchEvent(pointer('pointermove', 200, 100));
            expect(draft.highlightBox).toEqual(draft.previewBox);
        });

        it('creates the box with the height under the pointer on the last click', () => {
            const draft = startHeightStep();
            // The ray through pixel (200, 100) meets the plane through the centre (0, -6) at z = 3.
            canvas.dispatchEvent(pointer('pointermove', 200, 100));
            expect(draft.previewBox?.size[2]).toBeCloseTo(3);
            click(200, 100);
            expect(onCreate).toHaveBeenCalledOnce();
            const box = onCreate.mock.calls[0][0];
            expect(box.yaw).toBeCloseTo(Math.PI / 4);
            expect(box.center).toEqual([
                expect.closeTo(0),
                expect.closeTo(-6),
                expect.closeTo(1.5)
            ]);
            expect(box.size).toEqual([
                expect.closeTo(Math.sqrt(8)),
                expect.closeTo(Math.sqrt(8)),
                expect.closeTo(3)
            ]);
        });

        it('fits the height to the points when the camera looks straight down', () => {
            const batch = createBatch([
                [1, 0.5, 0.5],
                [1, 0.5, 2]
            ]);
            const { draft } = setup({
                cameraMode: 'perspective',
                camera: createDownCamera(),
                batch
            });
            pressAt(draft, 200, 200, [0, 0, 0]);
            canvas.dispatchEvent(pointer('pointermove', 240, 200));
            canvas.dispatchEvent(pointer('pointerup', 240, 200));
            canvas.dispatchEvent(pointer('pointermove', 240, 180));
            click(240, 180);
            expect(draft.previewBox?.size[2]).toBeCloseTo(1.5);
            click(240, 180);
            expect(onCreate.mock.calls[0][0].size).toEqual([
                expect.closeTo(2),
                expect.closeTo(1),
                expect.closeTo(1.5)
            ]);
        });

        it('fits the height to the points when the first pointer ray misses the height plane', () => {
            // The camera looks almost straight down. The footprint centre is below the screen
            // centre and the pointer above it, so the ray leaves the height plane behind.
            const camera = new PerspectiveCamera(90, 1, 0.1, 100);
            camera.position.set(0, 0, 10);
            camera.lookAt(0, 0.1, 0);
            camera.updateMatrixWorld();
            const batch = createBatch([
                [1, -1, 0.5],
                [1, -1, 2]
            ]);
            const { draft } = setup({ cameraMode: 'perspective', camera, batch });
            pressAt(draft, 200, 260, [0, -3, 0]);
            canvas.dispatchEvent(pointer('pointermove', 240, 260));
            canvas.dispatchEvent(pointer('pointerup', 240, 260));
            canvas.dispatchEvent(pointer('pointermove', 240, 180));
            click(240, 180);
            expect(draft.previewBox?.size[2]).toBeCloseTo(1.5);
            click(240, 180);
            expect(onCreate.mock.calls[0][0].size[2]).toBeCloseTo(1.5);
        });

        it('keeps the last preview when the ray misses the ground', () => {
            const { draft } = setup({
                cameraMode: 'perspective',
                camera: createHorizontalCamera()
            });
            pressAt(draft, 200, 300, [0, -8, 0]);
            canvas.dispatchEvent(pointer('pointermove', 250, 300));
            const preview = draft.previewBox;
            expect(preview).not.toBeNull();
            canvas.dispatchEvent(pointer('pointermove', 250, 100));
            expect(draft.previewBox).toEqual(preview);
        });
    });

    it.each(['Escape', 'contextmenu', 'pointercancel', 'lostpointercapture', 'unmount'])(
        'discards the draft on %s while the side is dragged',
        (reason) => {
            const { draft } = setup();
            dragSide(draft);
            if (reason === 'Escape')
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            else if (reason === 'unmount') cleanup();
            else canvas.dispatchEvent(pointer(reason, 300, 200));
            expect(draft.previewBox).toBeNull();
            canvas.dispatchEvent(pointer('pointerup', 300, 200));
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            click(300, 150);
            expect(onCreate).not.toHaveBeenCalled();
        }
    );

    it('prevents the context menu that follows a right-click cancellation, once', () => {
        const { draft } = setup();
        drawSideAndWidth(draft);
        click(300, 150, 2);
        const menu = pointer('contextmenu', 300, 150, 2);
        canvas.dispatchEvent(menu);
        expect(menu.defaultPrevented).toBe(true);
        const laterMenu = pointer('contextmenu', 300, 150, 2);
        canvas.dispatchEvent(laterMenu);
        expect(laterMenu.defaultPrevented).toBe(false);
    });

    it('prevents the context menu during a draft', () => {
        const { draft } = setup();
        dragSide(draft);
        const event = pointer('contextmenu', 300, 200);
        canvas.dispatchEvent(event);
        expect(event.defaultPrevented).toBe(true);
    });

    it.each([1, 2])('ignores a first pointer-down with button %i', (button) => {
        const { draft } = setup();
        pressAt(draft, 200, 200, [0, 0, 0], button);
        canvas.dispatchEvent(pointer('pointermove', 300, 200));
        expect(canvas.setPointerCapture).not.toHaveBeenCalled();
        expect(draft.previewBox).toBeNull();
    });

    it.each(['shiftKey', 'ctrlKey', 'metaKey'])(
        'leaves a first pointer-down with %s to the camera',
        (modifier) => {
            const { draft } = setup();
            const nativeEvent = pointer('pointerdown', 200, 200);
            Object.defineProperty(nativeEvent, modifier, { value: true });
            draft.handlePlanePointerDown({ point: { x: 0, y: 0, z: 0 }, nativeEvent });
            canvas.dispatchEvent(pointer('pointermove', 300, 200));
            expect(canvas.setPointerCapture).not.toHaveBeenCalled();
            expect(draft.previewBox).toBeNull();
        }
    );

    it('clears the preview when the pointer returns near the start', () => {
        const { draft } = setup();
        dragSide(draft);
        expect(draft.previewBox).not.toBeNull();
        canvas.dispatchEvent(pointer('pointermove', 201, 201));
        expect(draft.previewBox).toBeNull();
    });

    it('discards the draft when the batch changes', async () => {
        const { draft, rerender } = setup({ batch: createBatch([[1, 1, 0.25]]) });
        drawSideAndWidth(draft);
        const nextBatch = createBatch([[1, 1, 0.25]]);
        await rerender({ getBatch: () => nextBatch });
        expect(draft.previewBox).toBeNull();
        click(300, 150);
        expect(onCreate).not.toHaveBeenCalled();
    });

    it('discards the draft when the tick changes and the batch stays', async () => {
        const { draft, rerender } = setup();
        drawSideAndWidth(draft);
        await rerender({ getTick: () => 1 });
        expect(draft.previewBox).toBeNull();
        click(300, 150);
        expect(onCreate).not.toHaveBeenCalled();
    });

    it.each(['pointercancel', 'lostpointercapture'])(
        'keeps the draft on %s of a different pointer',
        (type) => {
            const { draft } = setup();
            dragSide(draft);
            canvas.dispatchEvent(pointer(type, 300, 200, 0, 8));
            expect(draft.previewBox).not.toBeNull();
        }
    );
});
