import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { OrthographicCamera } from 'three';
import CuboidDraftTarget from './CuboidDraftTarget.svelte';
import CuboidDraftGroupHarness from './CuboidDraftGroupHarness.svelte';

const mocks = vi.hoisted(() => ({
    useThrelte: vi.fn(),
    planePropsList: [] as Record<string, unknown>[],
    planeProps: null as Record<string, unknown> | null
}));
vi.mock('@threlte/core', () => ({
    useThrelte: mocks.useThrelte,
    // Every T element renders nothing; the invisible plane mesh keeps its props for the test.
    T: new Proxy(
        {},
        {
            get: (_target, element) => (_anchor: unknown, props: Record<string, unknown>) => {
                if (element === 'Mesh' && props.visible === false) {
                    mocks.planeProps = props;
                    mocks.planePropsList.push(props);
                }
            }
        }
    )
}));

let canvas: HTMLCanvasElement;
const onCreateCuboid = vi.fn();

beforeEach(() => {
    vi.clearAllMocks();
    mocks.planeProps = null;
    mocks.planePropsList = [];
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
    it('creates a cuboid immediately after a rectangle drag in Top, Side, or Front', () => {
        const cameras = [
            createTopCamera(),
            createProjectionCamera('front'),
            createProjectionCamera('side'),
            createTopCamera()
        ];
        for (const camera of cameras)
            mocks.useThrelte.mockReturnValueOnce({
                camera: { current: camera },
                renderer: { domElement: canvas }
            });
        const onHighlightChange = vi.fn(() => {
            if (onHighlightChange.mock.calls.length > 30)
                throw new Error('Highlight feedback loop');
        });
        render(CuboidDraftGroupHarness, {
            props: {
                onHighlightChange,
                onCreateCuboid
            }
        });
        for (const index of [3, 2, 1]) {
            const onpointerdown = mocks.planePropsList[index].onpointerdown as (
                event: unknown
            ) => void;
            onpointerdown({
                point: { x: 0, y: 0, z: 0 },
                nativeEvent: pointer('pointerdown', 200, 200)
            });
            canvas.dispatchEvent(pointer('pointermove', 300, 150));
            flushSync();
            canvas.dispatchEvent(pointer('pointerup', 300, 150));
            canvas.dispatchEvent(pointer('lostpointercapture', 300, 150));
            flushSync();
            expect(
                onCreateCuboid.mock.calls.at(-1)?.[0].size.every((extent: number) => extent > 0.1)
            ).toBe(true);
        }
        expect(onCreateCuboid).toHaveBeenCalledTimes(3);
    });

    it('keeps the active projection highlight when the owner updates idle viewports', () => {
        const onHighlightChange = vi.fn(() => {
            if (onHighlightChange.mock.calls.length > 20)
                throw new Error('Highlight feedback loop');
        });
        render(CuboidDraftGroupHarness, { props: { onHighlightChange } });
        onHighlightChange.mockClear();
        const onpointerdown = mocks.planeProps?.onpointerdown as (event: unknown) => void;
        onpointerdown({
            point: { x: 0.5, y: 0.5, z: 0 },
            nativeEvent: pointer('pointerdown', 225, 175)
        });
        canvas.dispatchEvent(pointer('pointermove', 325, 125));
        flushSync();
        expect(onHighlightChange).toHaveBeenCalledExactlyOnceWith(
            expect.objectContaining({ size: [expect.closeTo(2), expect.closeTo(1), Infinity] })
        );
    });

    it('creates a proportional box on rectangle release without another confirmation click', () => {
        dragOnPlane();
        expect(onCreateCuboid).not.toHaveBeenCalled();
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        expect(onCreateCuboid).toHaveBeenCalledExactlyOnceWith({
            center: [expect.closeTo(1.5), expect.closeTo(1), expect.closeTo(0.5)],
            size: [expect.closeTo(2), expect.closeTo(1), expect.closeTo(1)],
            yaw: 0
        });
    });

    it('reports the highlight region while drawing and clears it on release', () => {
        const onHighlightChange = vi.fn();
        dragOnPlane(0, onHighlightChange);
        flushSync();
        expect(onHighlightChange).toHaveBeenLastCalledWith(
            expect.objectContaining({ size: [expect.closeTo(2), expect.closeTo(1), Infinity] })
        );
        canvas.dispatchEvent(pointer('pointerup', 325, 125));
        flushSync();
        expect(onHighlightChange).toHaveBeenLastCalledWith(null);
    });

    it('does not create a cuboid from a line', () => {
        render(CuboidDraftTarget, {
            props: {
                bounds: { min: [-4, -4, 0], max: [4, 4, 2] },
                cameraMode: 'top',
                onCreateCuboid
            }
        });
        const onpointerdown = mocks.planeProps?.onpointerdown as (event: unknown) => void;
        onpointerdown({
            point: { x: 0, y: 0, z: 0 },
            nativeEvent: pointer('pointerdown', 200, 200)
        });
        canvas.dispatchEvent(pointer('pointerup', 300, 200));
        expect(onCreateCuboid).not.toHaveBeenCalled();
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
            if (cancel === 'Escape')
                window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            if (cancel === 'context menu')
                canvas.dispatchEvent(pointer('contextmenu', 325, 125, 2));
            canvas.dispatchEvent(pointer('pointerup', 325, 125));
            expect(onCreateCuboid).not.toHaveBeenCalled();
        }
    );
});

function createProjectionCamera(mode: 'side' | 'front'): OrthographicCamera {
    const camera = new OrthographicCamera(-4, 4, 4, -4, 0.1, 100);
    camera.up.set(0, 0, 1);
    camera.position.set(mode === 'side' ? 10 : 0, mode === 'front' ? -10 : 0, 0);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    return camera;
}
