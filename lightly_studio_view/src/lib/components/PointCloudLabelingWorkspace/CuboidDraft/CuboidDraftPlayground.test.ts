import { beforeEach, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { OrthographicCamera } from 'three';
import CuboidDraftPlayground from './CuboidDraftPlayground.svelte';

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
vi.mock('@threlte/extras', () => ({ interactivity: vi.fn() }));

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

it('draws a cuboid on the sample points and highlights the points that it takes in', () => {
    const batch = {
        positions: new Float32Array([1, 0.5, 0.25, 1, 0.5, 1.75]),
        intensities: new Float32Array(2),
        count: 2
    };
    render(CuboidDraftPlayground, {
        props: {
            cameraMode: 'top',
            batch,
            bounds: { min: [-4, -4, 0], max: [4, 4, 2] },
            onCreateCuboid
        }
    });
    const onpointerdown = mocks.planeProps?.onpointerdown as (event: unknown) => void;
    // Side from world (0, 0) to (2, 0), then a width of 1 toward +Y.
    onpointerdown({ point: { x: 0, y: 0, z: 0 }, nativeEvent: pointer('pointerdown', 200, 200) });
    canvas.dispatchEvent(pointer('pointermove', 300, 200));
    canvas.dispatchEvent(pointer('pointerup', 300, 200));
    canvas.dispatchEvent(pointer('pointermove', 300, 150));
    canvas.dispatchEvent(pointer('pointerdown', 300, 150));

    expect(onCreateCuboid).toHaveBeenCalledOnce();
    expect(onCreateCuboid.mock.calls[0][0].size).toEqual([
        expect.closeTo(2),
        expect.closeTo(1),
        expect.closeTo(1.5)
    ]);
});
