<script lang="ts">
    import { useParentObject3D } from '@threlte/core';
    import { TransformControls } from '@threlte/extras';
    import type { TransformControls as ThreeTransformControls } from 'three/examples/jsm/controls/TransformControls.js';
    import type { Object3D } from 'three';
    import {
        captureTransformSnapshot,
        restoreTransformSnapshot,
        getCuboidGizmoOptions
    } from './cuboidTransform';
    import type { CameraMode } from '../domain';

    interface Props {
        mode: 'translate' | 'rotate' | 'scale';
        cameraMode: CameraMode;
        enabled?: boolean;
        /** Called when the user finishes a drag; receives the mutated parent Object3D and a snapshot of its pre-drag transform. */
        onTransformEnd?: (
            object: Object3D,
            snapshot: ReturnType<typeof captureTransformSnapshot>
        ) => void;
        /** Called when the user starts interacting with the gizmo (mousedown on a handle). */
        onInteractionStart?: () => void;
        onInteractionCancel?: () => void;
    }

    let {
        mode,
        cameraMode,
        enabled = true,
        onTransformEnd,
        onInteractionStart,
        onInteractionCancel
    }: Props = $props();

    const parentObject3D = useParentObject3D();
    let controlsRef = $state<ThreeTransformControls | undefined>();
    const options = $derived(getCuboidGizmoOptions(mode, cameraMode));

    $effect(() => {
        const controls = controlsRef;
        if (!controls) return;

        let changed = false;
        let snapshot: ReturnType<typeof captureTransformSnapshot> | null = null;

        function onMouseDown(): void {
            changed = false;
            const obj = parentObject3D.current;
            snapshot = obj ? captureTransformSnapshot(obj) : null;
            onInteractionStart?.();
        }

        function onObjectChange(): void {
            changed = true;
        }

        function onMouseUp(): void {
            const obj = parentObject3D.current;
            if (changed && obj && snapshot) onTransformEnd?.(obj, snapshot);
            else onInteractionCancel?.();
            snapshot = null;
        }

        controls.addEventListener('mouseDown', onMouseDown);
        controls.addEventListener('objectChange', onObjectChange);
        controls.addEventListener('mouseUp', onMouseUp);
        return () => {
            controls.removeEventListener('mouseDown', onMouseDown);
            controls.removeEventListener('objectChange', onObjectChange);
            controls.removeEventListener('mouseUp', onMouseUp);
            const obj = parentObject3D.current;
            if (snapshot && obj) restoreTransformSnapshot(obj, snapshot);
            if (snapshot) onInteractionCancel?.();
        };
    });
</script>

<TransformControls
    bind:controls={controlsRef}
    {enabled}
    {mode}
    space={options.space}
    showX={options.showX}
    showY={options.showY}
    showZ={options.showZ}
    size={0.75}
    autoPauseControls={true}
    object={parentObject3D.current}
/>
