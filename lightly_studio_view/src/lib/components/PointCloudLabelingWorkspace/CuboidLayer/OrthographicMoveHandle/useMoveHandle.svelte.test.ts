import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Object3D, OrthographicCamera } from 'three';
import { render } from '@testing-library/svelte';
import { useMoveHandle } from './useMoveHandle.svelte';
import MoveHandleHarness from './MoveHandleHarness.svelte';

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

let cleanup: () => void = () => {};
let canvas: HTMLCanvasElement;
let object: Object3D;
const controls = { enabled: true };
const callbacks = {
    onTransformEnd: vi.fn(),
    onTransformPreview: vi.fn(),
    onInteractionStart: vi.fn(),
    onInteractionCancel: vi.fn()
};

beforeEach(() => {
    vi.clearAllMocks();
    canvas = document.createElement('canvas');
    canvas.getBoundingClientRect = () => new DOMRect(20, 30, 400, 200);
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
afterEach(() => cleanup());

function pointer(type: string, clientX: number, clientY: number) {
    const event = new MouseEvent(type, { clientX, clientY, buttons: 1, button: 0 });
    Object.defineProperty(event, 'pointerId', { value: 7 });
    return event as PointerEvent;
}

function startDrag() {
    const ref: { current?: ReturnType<typeof useMoveHandle> } = {};
    const instance = render(MoveHandleHarness, {
        props: {
            ...callbacks,
            onReady: (handle) => {
                ref.current = handle;
            }
        }
    });
    cleanup = () => {
        instance.unmount();
        cleanup = () => {};
    };
    ref.current!.onPointerDown({
        nativeEvent: pointer('pointerdown', 220, 130),
        stopPropagation: vi.fn()
    });
    // 50 px right at 0.02 world units per pixel.
    canvas.dispatchEvent(pointer('pointermove', 270, 130));
}

describe('orthographic move handle', () => {
    it('previews the move live and commits once on release', () => {
        startDrag();
        expect(controls.enabled).toBe(false);
        expect(object.position.x).toBeCloseTo(1);
        expect(callbacks.onTransformPreview).toHaveBeenCalledWith(object);
        canvas.dispatchEvent(pointer('pointerup', 270, 130));
        expect(callbacks.onInteractionStart).toHaveBeenCalledOnce();
        expect(callbacks.onTransformEnd).toHaveBeenCalledOnce();
        expect(callbacks.onInteractionCancel).not.toHaveBeenCalled();
        expect(controls.enabled).toBe(true);
    });

    it('restores the position on Escape', () => {
        startDrag();
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        expect(object.position.toArray()).toEqual([0, 0, 0]);
        expect(callbacks.onInteractionCancel).toHaveBeenCalledOnce();
        expect(callbacks.onTransformEnd).not.toHaveBeenCalled();
    });
});
