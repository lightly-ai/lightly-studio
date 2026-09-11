<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { DoubleSide, Group } from 'three';
    import type { Color } from 'three';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import { computeFaceConfigs, getFaceOpacity } from './cuboidResizeFaces';
    import { useCuboidResizeDrag } from './useCuboidResizeDrag.svelte';
    import CuboidWireframe from './CuboidWireframe.svelte';
    import type { CuboidAnnotation, CuboidHandle } from '$lib/components/PointCloudLabelingWorkspace/domain';

    /**
     * Renders six semi-transparent face planes for resize hover + drag interaction.
     * All pointer handling is managed by useCuboidResizeDrag via native DOM listeners
     * so pointerId and clientX/Y are always reliable. Fires `oncuboidupdate` once
     * on drag end with the resized annotation.
     */
    interface Props {
        /** Committed cuboid annotation; drag baseline. */
        annotation: CuboidAnnotation;
        /** Class color applied to face plane highlights and wireframe. */
        baseColor: string;
        /** Edge color including selection highlight. */
        edgeColor: Color;
        /** OrbitControls suppressed during drag. */
        orbitControls?: ThreeOrbitControls;
        /** Fires when the pointer enters or leaves a face handle. */
        onhover?: (annotationId: string | null, handle: CuboidHandle | null) => void;
        /** Fires once on drag end with the resized annotation. */
        oncuboidupdate?: (cuboid: CuboidAnnotation) => void;
        /** Fires on every preview change so the caller can follow the live position. */
        onliveupdate?: (cuboid: CuboidAnnotation) => void;
    }

    let { annotation, baseColor, edgeColor, orbitControls, onhover, oncuboidupdate, onliveupdate }: Props = $props();

    const { camera, renderer } = useThrelte();
    let facePlanesGroup = $state<Group | undefined>();

    const drag = useCuboidResizeDrag({
        getAnnotation: () => annotation,
        getOrbitControls: () => orbitControls,
        getCamera: () => camera.current,
        getRenderer: () => renderer,
        getFacePlanesGroup: () => facePlanesGroup,
        getOnhover: () => onhover,
        getOncuboidupdate: () => oncuboidupdate
    });

    $effect(() => {
        onliveupdate?.(drag.previewAnnotation);
    });

    const faceConfigs = $derived(computeFaceConfigs(drag.previewAnnotation.size));
</script>

<!-- Live wireframe + arrow tracks previewAnnotation so it updates during drag. -->
<CuboidWireframe annotation={drag.previewAnnotation} {edgeColor} {baseColor} />

<!-- Face planes positioned in the same local space as the live wireframe. -->
<T.Group position={[...drag.previewAnnotation.center]} quaternion={[...drag.previewAnnotation.rotation]}>
    <T.Group bind:ref={facePlanesGroup}>
        {#each faceConfigs as face (face.handle)}
            <T.Mesh position={face.position} rotation={face.euler}>
                <T.PlaneGeometry args={face.dims} />
                <T.MeshBasicMaterial
                    color={baseColor}
                    transparent={true}
                    opacity={getFaceOpacity(face.handle, drag.hoveredHandle, drag.activeDragHandle)}
                    side={DoubleSide}
                    depthWrite={false}
                />
            </T.Mesh>
        {/each}
    </T.Group>
</T.Group>
