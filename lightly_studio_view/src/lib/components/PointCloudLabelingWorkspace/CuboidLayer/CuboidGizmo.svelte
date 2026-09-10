<script lang="ts">
    import { TransformControls } from '@threlte/extras';
    import { Quaternion as ThreeQuaternion, Vector3 } from 'three';
    import type { Snippet } from 'svelte';
    import type { TransformControls as ThreeTransformControls } from 'three/examples/jsm/controls/TransformControls.js';
    import type { CuboidAnnotation, WorkspaceTool } from '../domain';

    /**
     * Wraps TransformControls for ground-plane-constrained translation and
     * free 3-axis rotation. The active tool determines the gizmo mode.
     *
     * Visual content is passed as `children` and rendered inside TransformControls'
     * internal attach-group, so it moves/rotates with the gizmo during drag. The
     * position or quaternion is captured on each `change` event (while
     * `dragging=true`) rather than on `mouseUp`, because Three.js fires `change`
     * with `dragging=false` before `mouseUp`, which can cause a Svelte re-render
     * that resets the group transform.
     */
    interface Props {
        /** The annotation whose geometry and position/rotation the gizmo controls. */
        annotation: CuboidAnnotation;
        /** Determines which gizmo mode is active: translate or rotate. */
        activeTool?: WorkspaceTool;
        /** Fires when a translate or rotate drag ends with the updated annotation. */
        oncuboidupdate?: (cuboid: CuboidAnnotation) => void;
        /** Visual content rendered inside the controlled group (moves with the gizmo). */
        children?: Snippet;
    }

    let { annotation, activeTool = 'translate', oncuboidupdate, children }: Props = $props();

    let controlsRef = $state<ThreeTransformControls>();

    /** World position captured on the last translate drag-move frame. */
    let lastDragPos: Vector3 | null = null;
    /** World quaternion captured on the last rotate drag-move frame. */
    let lastDragRot: ThreeQuaternion | null = null;

    $effect(() => {
        const controls = controlsRef;
        if (!controls) return;

        const tool = activeTool;

        function onChange(): void {
            if (!controls?.dragging || !controls.object) return;
            if (tool === 'rotate') {
                lastDragRot = controls.object.getWorldQuaternion(new ThreeQuaternion());
            } else {
                lastDragPos = controls.object.getWorldPosition(new Vector3());
            }
        }

        function onMouseUp(): void {
            if (tool === 'rotate') {
                if (!lastDragRot) return;
                oncuboidupdate?.({
                    ...annotation,
                    rotation: [lastDragRot.x, lastDragRot.y, lastDragRot.z, lastDragRot.w]
                });
                lastDragRot = null;
            } else {
                if (!lastDragPos) return;
                oncuboidupdate?.({
                    ...annotation,
                    center: [lastDragPos.x, lastDragPos.y, annotation.center[2]]
                });
                lastDragPos = null;
            }
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
    mode={activeTool === 'rotate' ? 'rotate' : 'translate'}
    space="world"
    autoPauseControls
    bind:controls={controlsRef}
>
    {@render children?.()}
</TransformControls>
