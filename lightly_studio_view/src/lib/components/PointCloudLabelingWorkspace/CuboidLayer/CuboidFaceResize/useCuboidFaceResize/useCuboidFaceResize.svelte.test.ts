import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Object3D, OrthographicCamera } from 'three';
import { render } from '@testing-library/svelte';
import { FACE_DEFINITIONS } from '../cuboidFaceResize';
import { useCuboidFaceResize } from './useCuboidFaceResize.svelte';
import CuboidFaceResizeHarness from './CuboidFaceResizeHarness.svelte';

const mocks = vi.hoisted(() => ({
    useThrelte: vi.fn(),
    useParentObject3D: vi.fn(),
    useOrbitControls: vi.fn()
}));
vi.mock('@threlte/core', () => ({
    useThrelte: mocks.useThrelte,
    useParentObject3D: mocks.useParentObject3D
}));
vi.mock('@threlte/extras', () => ({ useOrbitControls: mocks.useOrbitControls }));

const annotation = {
    id: 'ann-a',
    frameId: 'frame-1',
    center: [0, 0, 0] as [number, number, number],
    size: [2, 3, 4] as [number, number, number],
    rotation: [0, 0, 0, 1] as [number, number, number, number]
};
const PLUS_X_FACE = FACE_DEFINITIONS[0];

let cleanup: () => void;
let canvas: HTMLCanvasElement;
let object: Object3D;
const controls = { enabled: true };
const callbacks = {
    onResizeStart: vi.fn(),
    onResizeCancel: vi.fn(),
    onResizePreview: vi.fn(),
    onResizeEnd: vi.fn()
};

beforeEach(() => {
    vi.clearAllMocks();
    canvas = document.createElement('canvas');
    // Orthographic camera spans x in [-4, 4] over a 400px wide canvas: 50px per meter.
    canvas.getBoundingClientRect = () => new DOMRect(0, 0, 400, 200);
    canvas.setPointerCapture = vi.fn();
    canvas.hasPointerCapture = () => true;
    canvas.releasePointerCapture = vi.fn();
    object = new Object3D();
    controls.enabled = true;
    const camera = new OrthographicCamera(-4, 4, 2, -2);
    camera.position.z = 10;
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    mocks.useThrelte.mockReturnValue({
        camera: { current: camera },
        renderer: { domElement: canvas },
        invalidate: vi.fn()
    });
    mocks.useParentObject3D.mockReturnValue({ current: object });
    mocks.useOrbitControls.mockReturnValue({ current: controls });
});
afterEach(() => cleanup?.());

function pointer(type: string, clientX: number, clientY: number) {
    const event = new MouseEvent(type, { clientX, clientY, buttons: 1, button: 0 });
    Object.defineProperty(event, 'pointerId', { value: 7 });
    return event as PointerEvent;
}

function startDrag(downEvent = pointer('pointerdown', 250, 100)) {
    const ref: { current?: ReturnType<typeof useCuboidFaceResize> } = {};
    const instance = render(CuboidFaceResizeHarness, {
        props: {
            ...callbacks,
            getAnnotation: () => annotation,
            onReady: (resize) => {
                ref.current = resize;
            }
        }
    });
    cleanup = () => {
        instance.unmount();
        cleanup = () => {};
    };
    const resize = ref.current!;
    // Grab the +X face at world (1, 0, 0), which sits at pixel x=250.
    resize.onFacePointerDown({
        face: PLUS_X_FACE,
        event: {
            point: { x: 1, y: 0, z: 0 },
            nativeEvent: downEvent,
            stopPropagation: vi.fn()
        } as unknown as Parameters<typeof resize.onFacePointerDown>[0]['event']
    });
    // Drag one meter outward along +X.
    canvas.dispatchEvent(pointer('pointermove', 300, 100));
    return resize;
}

describe('cuboid face resize interaction', () => {
    it('keeps other canvas pointer handlers from starting a second drag', () => {
        const downEvent = pointer('pointerdown', 250, 100);
        const stopImmediatePropagation = vi.spyOn(downEvent, 'stopImmediatePropagation');
        startDrag(downEvent);
        expect(stopImmediatePropagation).toHaveBeenCalledOnce();
    });

    it('previews the resize through the annotation without scaling the group', () => {
        startDrag();
        expect(controls.enabled).toBe(false);
        expect(callbacks.onResizeStart).toHaveBeenCalledOnce();
        expect(callbacks.onResizePreview).toHaveBeenLastCalledWith({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            rotation: [0, 0, 0, 1],
            center: [0.5, 0, 0],
            size: [3, 3, 4]
        });
        // The previewed annotation already renders at the new size, so scaling the
        // group on top of it would grow the cuboid twice and move the opposite face.
        expect(object.scale.toArray()).toEqual([1, 1, 1]);
        expect(object.position.toArray()).toEqual([0, 0, 0]);
    });

    it('commits the last previewed transform once on release', () => {
        startDrag();
        canvas.dispatchEvent(pointer('pointerup', 300, 100));
        expect(callbacks.onResizeEnd).toHaveBeenCalledOnce();
        expect(callbacks.onResizeEnd).toHaveBeenCalledWith({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            rotation: [0, 0, 0, 1],
            center: [0.5, 0, 0],
            size: [3, 3, 4]
        });
        expect(callbacks.onResizeCancel).not.toHaveBeenCalled();
        expect(controls.enabled).toBe(true);
        expect(canvas.releasePointerCapture).toHaveBeenCalledWith(7);
    });

    it.each(['Escape', 'pointercancel', 'lostpointercapture', 'unmount'])(
        'cancels the resize and restores camera controls on %s',
        (reason) => {
            startDrag();
            if (reason === 'Escape')
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            else if (reason === 'unmount') cleanup();
            else canvas.dispatchEvent(pointer(reason, 300, 100));
            expect(controls.enabled).toBe(true);
            expect(callbacks.onResizeCancel).toHaveBeenCalledOnce();
            expect(callbacks.onResizeEnd).not.toHaveBeenCalled();
        }
    );
});
