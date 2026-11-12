import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { OrthographicCamera } from 'three';
import CuboidDraftTarget from './CuboidDraftTarget.svelte';

const mocks = vi.hoisted(() => ({
    useThrelte: vi.fn(),
    planeProps: null as Record<string, unknown> | null
}));
vi.mock('@threlte/core', () => ({
    useThrelte: mocks.useThrelte,
    // Every T element renders nothing; the invisible plane mesh keeps its props for the test.
    T: new Proxy(
        {},
        {
            get: (_target, element) => (_anchor: unknown, props: Record<string, unknown>) => {
                if (element === 'Mesh' && props.visible === false) mocks.planeProps = props;
            }
        }
    )
}));

let canvas: HTMLCanvasElement;
const onCreateCuboid = vi.fn();

beforeEach(() => {
    vi.clearAllMocks();
    mocks.planeProps = null;
    canvas = document.createElement('canvas');
    canvas.getBoundingClientRect = () => new DOMRect(0, 0, 400, 400);
    canvas.setPointerCapture = vi.fn();
    canvas.hasPointerCapture = () => true;
    canvas.releasePointerCapture = vi.fn();
    mocks.useThrelte.mockReturnValue({
        camera: { current: createTopCamera() },
        renderer: { domElement: canvas }
    });
});

/** Looks down −Z; spans [-4, 4] on x and y over 400 px: 50 px per meter, pixel (200, 200) is the origin. */
function createTopCamera(): OrthographicCamera {
    const camera = new OrthographicCamera(-4, 4, 4, -4, 0.1, 100);
    camera.position.set(0, 0, 10);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    return camera;
}

function pointer(type: string, clientX: number, clientY: number, button = 0): PointerEvent {
    const event = new MouseEvent(type, { clientX, clientY, button, buttons: 1, cancelable: true });
    Object.defineProperty(event, 'pointerId', { value: 7 });
    return event as PointerEvent;
}

/** Presses on the plane at world (0.5, 0.5, 0) and drags to world (2.5, 1.5, 0). */
function dragOnPlane(button = 0, onHighlightChange?: (box: unknown) => void): void {
    render(CuboidDraftTarget, {
        props: {
            bounds: { min: [-4, -4, 0], max: [4, 4, 2] },
            cameraMode: 'top',
            onHighlightChange,
            onCreateCuboid
        }
    });
    const onpointerdown = mocks.planeProps?.onpointerdown as (event: unknown) => void;
    onpointerdown({
        point: { x: 0.5, y: 0.5, z: 0 },
        nativeEvent: pointer('pointerdown', 225, 175, button)
    });
    canvas.dispatchEvent(pointer('pointermove', 325, 125));
}

describe('CuboidDraftTarget', () => {
    it('creates an angled box from a dragged side and a width click', () => {
        dragOnPlane();
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        canvas.dispatchEvent(pointer('pointermove', 325, 75));
        canvas.dispatchEvent(pointer('pointerdown', 325, 75));
        expect(onCreateCuboid).toHaveBeenCalledOnce();
        const box = onCreateCuboid.mock.calls[0][0];
        expect(box.yaw).toBeCloseTo(Math.atan2(1, 2));
        expect(box.size[0]).toBeCloseTo(Math.sqrt(5));
        expect(box.size[1]).toBeCloseTo(2 / Math.sqrt(5));
    });

    it('reports the highlight region while drawing and clears it at the end', () => {
        const onHighlightChange = vi.fn();
        dragOnPlane(0, onHighlightChange);
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        canvas.dispatchEvent(pointer('pointermove', 325, 75));
        flushSync();
        expect(onHighlightChange).toHaveBeenLastCalledWith(
            expect.objectContaining({ yaw: expect.closeTo(Math.atan2(1, 2)) })
        );
        canvas.dispatchEvent(pointer('pointerdown', 325, 75));
        flushSync();
        expect(onHighlightChange).toHaveBeenLastCalledWith(null);
    });

    it('does not write to its owner while it is destroyed', () => {
        const onHighlightChange = vi.fn();
        const { unmount } = render(CuboidDraftTarget, {
            props: {
                bounds: { min: [-4, -4, 0], max: [4, 4, 2] },
                onHighlightChange,
                onCreateCuboid
            }
        });
        flushSync();
        onHighlightChange.mockClear();
        unmount();
        expect(onHighlightChange).not.toHaveBeenCalled();
    });

    it.each(['Escape', 'context menu', 'right-button drag'])(
        'creates nothing after %s',
        (cancel) => {
            dragOnPlane(cancel === 'right-button drag' ? 2 : 0);
            canvas.dispatchEvent(pointer('pointerup', 325, 125));
            if (cancel === 'Escape')
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            if (cancel === 'context menu')
                canvas.dispatchEvent(pointer('contextmenu', 325, 125, 2));
            canvas.dispatchEvent(pointer('pointerdown', 325, 75));
            expect(onCreateCuboid).not.toHaveBeenCalled();
        }
    );
});
