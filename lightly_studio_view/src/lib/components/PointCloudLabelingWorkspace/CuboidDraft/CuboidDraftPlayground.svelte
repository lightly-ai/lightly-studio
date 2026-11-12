<script lang="ts">
    import { T } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import * as THREE from 'three';
    import type { Bounds3, CameraMode } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { PointBatch } from '$lib/components/PointCloudViewer';
    import type { CuboidBox } from './cuboidDraft';
    import CuboidDraftPreview from './CuboidDraftPreview.svelte';
    import CuboidDraftTarget from './CuboidDraftTarget.svelte';

    /**
     * Scene for Storybook: draws cuboids on a point cloud without the workspace around it.
     * Mount it after the camera controls, as the workspace does, so that the draft keeps the
     * pointer capture.
     */
    interface Props {
        /** View in which the cuboid is drawn. */
        cameraMode: CameraMode;
        /** Points shown in the scene and used to fit a drawn cuboid. */
        batch: PointBatch;
        /** Bounds of the points; they place the drawing plane. */
        bounds: Bounds3;
        /** Fires with each drawn box. */
        onCreateCuboid?: (box: CuboidBox) => void;
    }

    let { cameraMode, batch, bounds, onCreateCuboid }: Props = $props();
    let boxes = $state<CuboidBox[]>([]);
    const pointGeometry = $derived(
        new THREE.BufferGeometry().setAttribute(
            'position',
            new THREE.BufferAttribute(batch.positions, 3)
        )
    );

    interactivity();
</script>

<T.Color attach="background" args={['#10141c']} />
<T.GridHelper args={[24, 24, '#344054', '#202938']} rotation={[Math.PI / 2, 0, 0]} />
<T.Points geometry={pointGeometry}>
    <T.PointsMaterial color="#7dd3fc" size={3} sizeAttenuation={false} />
</T.Points>
<CuboidDraftTarget
    {bounds}
    {cameraMode}
    {batch}
    onCreateCuboid={(box) => {
        boxes.push(box);
        onCreateCuboid?.(box);
    }}
/>
{#each boxes as box, index (index)}
    <CuboidDraftPreview {box} />
{/each}
