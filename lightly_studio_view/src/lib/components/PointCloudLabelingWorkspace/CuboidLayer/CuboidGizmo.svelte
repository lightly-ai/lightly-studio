<script lang="ts">
    import { useParentObject3D } from '@threlte/core';
    import { TransformControls } from '@threlte/extras';
    import type { TransformControls as ThreeTransformControls } from 'three/examples/jsm/controls/TransformControls.js';
    import type { Object3D } from 'three';

    interface Props {
        mode: 'translate' | 'rotate' | 'scale';
        enabled?: boolean;
        /** Called when the user finishes a drag; receives the mutated parent Object3D. */
        onTransformEnd?: (object: Object3D) => void;
        /** Called when the user starts interacting with the gizmo (mousedown on a handle). */
        onInteractionStart?: () => void;
    }

    let { mode, enabled = true, onTransformEnd, onInteractionStart }: Props = $props();

    const parentObject3D = useParentObject3D();
    let controlsRef = $state<ThreeTransformControls | undefined>();

    $effect(() => {
        const controls = controlsRef;
        if (!controls) return;

        function onMouseDown() {
            onInteractionStart?.();
        }

        function onMouseUp() {
            const obj = parentObject3D.current;
            if (obj) onTransformEnd?.(obj);
        }

        controls.addEventListener('mouseDown', onMouseDown);
        controls.addEventListener('mouseUp', onMouseUp);
        return () => {
            controls.removeEventListener('mouseDown', onMouseDown);
            controls.removeEventListener('mouseUp', onMouseUp);
        };
    });
</script>

<TransformControls
    bind:controls={controlsRef}
    {enabled}
    {mode}
    space="local"
    size={0.75}
    autoPauseControls={true}
    object={parentObject3D.current}
/>
