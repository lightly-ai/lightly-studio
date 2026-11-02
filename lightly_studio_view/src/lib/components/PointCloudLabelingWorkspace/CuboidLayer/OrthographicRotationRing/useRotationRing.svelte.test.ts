import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Object3D, OrthographicCamera, Quaternion } from 'three';
import { render } from '@testing-library/svelte';
import { useRotationRing } from './useRotationRing.svelte';
import RotationRingHarness from './RotationRingHarness.svelte';

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

let cleanup: () => void;
let canvas: HTMLCanvasElement;
let object: Object3D;
const controls = { enabled: true };
const callbacks = {
    onTransformEnd: vi.fn(),
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

function startDrag() {
    const ref: { current?: ReturnType<typeof useRotationRing> } = {};
    const instance = render(RotationRingHarness, {
        props: {
            ...callbacks,
            onReady: (ring) => {
                ref.current = ring;
            }
        }
    });
    cleanup = () => {
        instance.unmount();
        cleanup = () => {};
    };
    const ring = ref.current!;
    ring.onPointerDown({
        nativeEvent: pointer('pointerdown', 300, 130),
        stopPropagation: vi.fn()
    });
    canvas.dispatchEvent(pointer('pointermove', 220, 50));
    return ring;
}

describe('rotation ring interaction', () => {
    it('previews rotation, pauses camera controls, and commits once on release', () => {
        startDrag();
        expect(controls.enabled).toBe(false);
        expect(object.quaternion.angleTo(new Quaternion())).toBeCloseTo(Math.PI / 2);
        canvas.dispatchEvent(pointer('pointerup', 220, 50));
        expect(callbacks.onTransformEnd).toHaveBeenCalledOnce();
        expect(callbacks.onInteractionStart).toHaveBeenCalledOnce();
        expect(callbacks.onInteractionCancel).not.toHaveBeenCalled();
        expect(controls.enabled).toBe(true);
        expect(canvas.releasePointerCapture).toHaveBeenCalledWith(7);
    });

    it.each(['Escape', 'pointercancel', 'lostpointercapture', 'unmount'])(
        'restores the annotation and camera controls on %s',
        (reason) => {
            startDrag();
            if (reason === 'Escape')
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            else if (reason === 'unmount') cleanup();
            else canvas.dispatchEvent(pointer(reason, 220, 50));
            expect(object.quaternion.angleTo(new Quaternion())).toBeCloseTo(0);
            expect(controls.enabled).toBe(true);
            expect(callbacks.onInteractionCancel).toHaveBeenCalledOnce();
            expect(callbacks.onTransformEnd).not.toHaveBeenCalled();
        }
    );
});
