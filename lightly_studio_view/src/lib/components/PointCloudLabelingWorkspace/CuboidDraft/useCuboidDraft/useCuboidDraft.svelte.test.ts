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

function pointer(type: string, clientX: number, clientY: number, button = 0) {
    const event = new MouseEvent(type, {
        clientX,
        clientY,
        button,
        buttons: 1,
        cancelable: true
    });
    Object.defineProperty(event, 'pointerId', { value: 7 });
    return event as PointerEvent;
}

interface SetupOptions {
    cameraMode?: CameraMode;
    camera?: Camera;
    batch?: PointBatch;
}

function setup({ cameraMode = 'top', camera = createTopCamera(), batch }: SetupOptions = {}) {
    mocks.useThrelte.mockReturnValue({
        camera: { current: camera },
        renderer: { domElement: canvas }
    });
    const ref: { current?: Draft } = {};
    const instance = render(CuboidDraftHarness, {
        props: {
            getCameraMode: () => cameraMode,
            getBatch: () => batch,
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

/** Drags from world (0.5, 0.5, 0) to world (2.5, 1.5, 0) in the top view. */
function dragInTopView(draft: Draft) {
    pressAt(draft, 225, 175, [0.5, 0.5, 0]);
    canvas.dispatchEvent(pointer('pointermove', 325, 125));
}

/**
 * Drags a footprint from world (0, -8, 0) to world (2, -6, 0) on the ground with the horizontal
 * camera and releases it, which starts the height step in the perspective view.
 */
function startHeightStep() {
    const { draft } = setup({ cameraMode: 'perspective', camera: createHorizontalCamera() });
    pressAt(draft, 200, 300, [0, -8, 0]);
    canvas.dispatchEvent(pointer('pointermove', 300, 250));
    canvas.dispatchEvent(pointer('pointerup', 300, 250));
    return draft;
}

describe('useCuboidDraft', () => {
    it('drops a default cuboid on a click', () => {
        const { draft } = setup();
        pressAt(draft, 200, 200, [0, 0, 0]);
        canvas.dispatchEvent(pointer('pointerup', 201, 201));
        expect(onCreate).toHaveBeenCalledOnce();
        expect(onCreate).toHaveBeenCalledWith({ kind: 'drop', position: [0, 0, 0] });
    });

    it('creates a fitted box after a drag in the top view', () => {
        const batch = createBatch([
            [1, 1, 0.25],
            [2, 1, 1.75]
        ]);
        const { draft } = setup({ batch });
        dragInTopView(draft);
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        expect(onCreate).toHaveBeenCalledOnce();
        const placement = onCreate.mock.calls[0][0];
        expect(placement.kind).toBe('box');
        expect(placement.box.size[2]).toBeCloseTo(1.5);
        expect(placement.box.center[2]).toBeCloseTo(1);
    });

    it('shows a flat preview while dragging and clears it on release', () => {
        const { draft } = setup();
        dragInTopView(draft);
        expect(draft.previewBox?.size[2]).toBeCloseTo(0.1);
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        expect(draft.previewBox).toBeNull();
    });

    it('keeps the footprint preview after the drag in the perspective view', () => {
        const draft = startHeightStep();
        expect(onCreate).not.toHaveBeenCalled();
        expect(draft.previewBox).not.toBeNull();
    });

    it('sets the height from pointer movement and saves on click', () => {
        const draft = startHeightStep();
        canvas.dispatchEvent(pointer('pointermove', 200, 100));
        canvas.dispatchEvent(pointer('pointerdown', 200, 100));
        expect(onCreate).toHaveBeenCalledOnce();
        const placement = onCreate.mock.calls[0][0];
        expect(placement.kind).toBe('box');
        expect(placement.box.size[2]).toBeGreaterThan(0.1);
        expect(placement.box.center[2]).toBeCloseTo(placement.box.size[2] / 2);
        expect(draft.previewBox).toBeNull();
    });

    it('keeps the height step when the drag releases its pointer capture', () => {
        const draft = startHeightStep();
        canvas.dispatchEvent(pointer('lostpointercapture', 300, 250));
        expect(draft.previewBox).not.toBeNull();
        canvas.dispatchEvent(pointer('pointerdown', 200, 100));
        expect(onCreate).toHaveBeenCalledOnce();
    });

    it.each(['Escape', 'contextmenu', 'right pointer-down', 'pointercancel'])(
        'discards the height step on %s',
        (reason) => {
            const draft = startHeightStep();
            if (reason === 'Escape')
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            else if (reason === 'right pointer-down')
                canvas.dispatchEvent(pointer('pointerdown', 200, 100, 2));
            else canvas.dispatchEvent(pointer(reason, 200, 100));
            expect(draft.previewBox).toBeNull();
            canvas.dispatchEvent(pointer('pointerdown', 200, 100));
            expect(onCreate).not.toHaveBeenCalled();
        }
    );

    it('does not start a second draft during the height step', () => {
        const draft = startHeightStep();
        const preview = draft.previewBox;
        pressAt(draft, 100, 300, [-1, -8, 0]);
        expect(draft.previewBox).toEqual(preview);
        canvas.dispatchEvent(pointer('pointermove', 200, 100));
        expect(draft.previewBox?.size[2]).toBeGreaterThan(0.1);
    });

    it('does not start a new draft from the click that saves the height step', () => {
        const draft = startHeightStep();
        const click = pointer('pointerdown', 200, 100);
        canvas.dispatchEvent(click);
        draft.handlePlanePointerDown({ point: { x: 0, y: -8, z: 0 }, nativeEvent: click });
        canvas.dispatchEvent(pointer('pointermove', 300, 250));
        expect(onCreate).toHaveBeenCalledOnce();
        expect(draft.previewBox).toBeNull();
    });

    it.each(['Escape', 'contextmenu', 'pointercancel', 'lostpointercapture', 'unmount'])(
        'discards the draft on %s',
        (reason) => {
            const { draft } = setup();
            dragInTopView(draft);
            if (reason === 'Escape')
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            else if (reason === 'unmount') cleanup();
            else canvas.dispatchEvent(pointer(reason, 325, 125));
            expect(draft.previewBox).toBeNull();
            canvas.dispatchEvent(pointer('pointerup', 325, 125));
            expect(onCreate).not.toHaveBeenCalled();
        }
    );

    it('prevents the context menu during a draft', () => {
        const { draft } = setup();
        dragInTopView(draft);
        const event = pointer('contextmenu', 325, 125);
        canvas.dispatchEvent(event);
        expect(event.defaultPrevented).toBe(true);
    });

    it.each([1, 2])('ignores pointer-down with button %i', (button) => {
        const { draft } = setup();
        pressAt(draft, 225, 175, [0.5, 0.5, 0], button);
        canvas.dispatchEvent(pointer('pointermove', 325, 125));
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        expect(onCreate).not.toHaveBeenCalled();
        expect(draft.previewBox).toBeNull();
    });

    it.each(['shiftKey', 'ctrlKey', 'metaKey'])(
        'leaves a pointer-down with %s to the camera',
        (modifier) => {
            const { draft } = setup();
            const nativeEvent = pointer('pointerdown', 225, 175);
            Object.defineProperty(nativeEvent, modifier, { value: true });
            draft.handlePlanePointerDown({ point: { x: 0.5, y: 0.5, z: 0 }, nativeEvent });
            canvas.dispatchEvent(pointer('pointermove', 325, 125));
            canvas.dispatchEvent(pointer('pointerup', 325, 125));
            expect(canvas.setPointerCapture).not.toHaveBeenCalled();
            expect(draft.previewBox).toBeNull();
            expect(onCreate).not.toHaveBeenCalled();
        }
    );

    it('clears the preview when the pointer returns near the start', () => {
        const { draft } = setup();
        dragInTopView(draft);
        expect(draft.previewBox).not.toBeNull();
        canvas.dispatchEvent(pointer('pointermove', 226, 176));
        expect(draft.previewBox).toBeNull();
        canvas.dispatchEvent(pointer('pointerup', 226, 176));
        expect(onCreate).toHaveBeenCalledWith({ kind: 'drop', position: [0.5, 0.5, 0] });
    });

    it('creates nothing after a long drag whose rays all miss the plane', () => {
        // The top-view plane is horizontal; this camera's rays above the horizon never reach it.
        const { draft } = setup({ camera: createHorizontalCamera() });
        pressAt(draft, 200, 300, [0, 0, 0]);
        canvas.dispatchEvent(pointer('pointermove', 250, 100));
        canvas.dispatchEvent(pointer('pointerup', 250, 100));
        expect(onCreate).not.toHaveBeenCalled();
    });

    it('keeps the last preview when the ray misses the plane', () => {
        const { draft } = setup({ cameraMode: 'perspective', camera: createHorizontalCamera() });
        pressAt(draft, 200, 300, [0, 0, 0]);
        canvas.dispatchEvent(pointer('pointermove', 250, 300));
        const preview = draft.previewBox;
        expect(preview).not.toBeNull();
        canvas.dispatchEvent(pointer('pointermove', 250, 100));
        expect(draft.previewBox).toEqual(preview);
    });

    it('discards the draft when the batch changes', async () => {
        const { draft, rerender } = setup({ batch: createBatch([[1, 1, 0.25]]) });
        dragInTopView(draft);
        const nextBatch = createBatch([[1, 1, 0.25]]);
        await rerender({ getBatch: () => nextBatch });
        expect(draft.previewBox).toBeNull();
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        expect(onCreate).not.toHaveBeenCalled();
    });
});
