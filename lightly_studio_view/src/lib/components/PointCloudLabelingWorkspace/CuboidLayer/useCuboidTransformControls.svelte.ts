import { useParentObject3D } from '@threlte/core';
import type { Object3D } from 'three';
import type { TransformControls } from 'three/examples/jsm/controls/TransformControls.js';
import { captureTransformSnapshot, restoreTransformSnapshot } from './cuboidTransform';

interface Params {
    getControls: () => TransformControls | undefined;
    onTransformEnd?: (
        object: Object3D,
        snapshot: ReturnType<typeof captureTransformSnapshot>
    ) => void;
    onInteractionStart?: () => void;
    onInteractionCancel?: () => void;
}

export function useCuboidTransformControls(params: Params): void {
    const parent = useParentObject3D();
    $effect(() => {
        const controls = params.getControls();
        if (!controls) return;
        let changed = false;
        let snapshot: ReturnType<typeof captureTransformSnapshot> | null = null;

        function onMouseDown(): void {
            changed = false;
            snapshot = parent.current ? captureTransformSnapshot(parent.current) : null;
            params.onInteractionStart?.();
        }

        function onObjectChange(): void {
            changed = true;
        }

        function onMouseUp(): void {
            if (changed && parent.current && snapshot)
                params.onTransformEnd?.(parent.current, snapshot);
            else params.onInteractionCancel?.();
            snapshot = null;
        }

        controls.addEventListener('mouseDown', onMouseDown);
        controls.addEventListener('objectChange', onObjectChange);
        controls.addEventListener('mouseUp', onMouseUp);
        return () => {
            controls.removeEventListener('mouseDown', onMouseDown);
            controls.removeEventListener('objectChange', onObjectChange);
            controls.removeEventListener('mouseUp', onMouseUp);
            if (snapshot && parent.current) restoreTransformSnapshot(parent.current, snapshot);
            if (snapshot) params.onInteractionCancel?.();
        };
    });
}
