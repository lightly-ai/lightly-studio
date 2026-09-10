<script lang="ts">
    import { TransformControls } from '@threlte/extras';
    import { Vector3 } from 'three';
    import type { Snippet } from 'svelte';
    import type { TransformControls as ThreeTransformControls } from 'three/examples/jsm/controls/TransformControls.js';
    import type { CuboidAnnotation } from '../domain';

    /**
     * Wraps TransformControls for ground-plane-constrained translation.
     *
     * Visual content is passed as `children` and rendered inside TransformControls'
     * internal attach-group, so it moves with the gizmo during drag. The position
     * is captured on each `change` event (while `dragging=true`) rather than on
     * `mouseUp`, because Three.js fires `change` with `dragging=false` before
     * `mouseUp`, which can cause a Svelte re-render that resets the group position.
     */
    interface Props {
        /** The annotation whose geometry and position the gizmo controls. */
        annotation: CuboidAnnotation;
        /** Fires when a translate drag ends with the updated annotation. */
        oncuboidupdate?: (cuboid: CuboidAnnotation) => void;
        /** Visual content rendered inside the controlled group (moves with the gizmo). */
        children?: Snippet;
    }

    let { annotation, oncuboidupdate, children }: Props = $props();

    let controlsRef = $state<ThreeTransformControls>();

    /** World position of the controlled group on the last drag-move frame. */
    let lastDragPos: Vector3 | null = null;

    $effect(() => {
        const controls = controlsRef;
        if (!controls) return;

        function onChange(): void {
            if (controls?.dragging && controls.object) {
                lastDragPos = controls.object.getWorldPosition(new Vector3());
            }
        }

        function onMouseUp(): void {
            if (!lastDragPos) return;
            oncuboidupdate?.({
                ...annotation,
                center: [lastDragPos.x, lastDragPos.y, annotation.center[2]]
            });
            lastDragPos = null;
        }

        controls.addEventListener('change', onChange);
        controls.addEventListener('mouseUp', onMouseUp);
        return () => {
            controls.removeEventListener('change', onChange);
            controls.removeEventListener('mouseUp', onMouseUp);
        };
    });
</script>

<!--
    position + quaternion go to the attach-group (objectProps in Threlte's
    TransformControls), placing it at the cuboid's initial centre and orientation.
-->
<TransformControls
    position={[...annotation.center]}
    quaternion={[...annotation.rotation]}
    mode="translate"
    space="world"
    autoPauseControls
    bind:controls={controlsRef}
>
    {@render children?.()}
</TransformControls>
