import { describe, expect, it } from 'vitest';
import { Object3D, OrthographicCamera, Quaternion, Vector3 } from 'three';
import { applyMoveDrag, createMoveDrag } from './moveHandle';

function setup(parentRotation = new Quaternion()) {
    const camera = new OrthographicCamera(-4, 4, 2, -2);
    camera.position.z = 10;
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    const canvas = document.createElement('canvas');
    // 400x200 px for an 8x4 world-unit view: 0.02 world units per pixel.
    canvas.getBoundingClientRect = () => new DOMRect(20, 30, 400, 200);
    const parent = new Object3D();
    parent.quaternion.copy(parentRotation);
    const object = new Object3D();
    parent.add(object);
    parent.updateMatrixWorld();
    return { camera, canvas, object };
}

function pointer(clientX: number, clientY: number) {
    const event = new MouseEvent('pointermove', { clientX, clientY });
    Object.defineProperty(event, 'pointerId', { value: 7 });
    return event as PointerEvent;
}

describe('orthographic move drag', () => {
    it('moves the cuboid with the pointer in the screen plane', () => {
        const { camera, canvas, object } = setup();
        const drag = createMoveDrag({ object, camera, canvas, event: pointer(220, 130) });
        expect(applyMoveDrag(drag, pointer(270, 80))).toBe(true);
        expect(object.position.toArray()).toEqual([
            expect.closeTo(1),
            expect.closeTo(1),
            expect.closeTo(0)
        ]);
    });

    it('converts the screen motion into the parent space', () => {
        const quarterTurn = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI / 2);
        const { camera, canvas, object } = setup(quarterTurn);
        const drag = createMoveDrag({ object, camera, canvas, event: pointer(220, 130) });
        applyMoveDrag(drag, pointer(270, 130));
        expect(object.getWorldPosition(new Vector3()).toArray()).toEqual([
            expect.closeTo(1),
            expect.closeTo(0),
            expect.closeTo(0)
        ]);
    });

    it('reports no change while the pointer has not moved', () => {
        const { camera, canvas, object } = setup();
        const drag = createMoveDrag({ object, camera, canvas, event: pointer(220, 130) });
        expect(applyMoveDrag(drag, pointer(220, 130))).toBe(false);
        expect(object.position.toArray()).toEqual([0, 0, 0]);
    });
});
