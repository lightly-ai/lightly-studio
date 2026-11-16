<script lang="ts">
    import { T } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import * as THREE from 'three';
    import type { Bounds3, CameraMode } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { PointBatch } from '$lib/components/PointCloudViewer';
    import { getPointCloudFrameColors } from '$lib/components/PointCloudViewer/getPointCloudFrameColors';
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
    let highlight = $state.raw<CuboidBox | null>(null);
    // The workspace colors the points in the same way while a cuboid is drawn.
    const colors = $derived(
        getPointCloudFrameColors(
            batch,
            'none',
            undefined,
            undefined,
            highlight
                ? {
                      center: highlight.center,
                      size: highlight.size,
                      rotation: [0, 0, Math.sin(highlight.yaw / 2), Math.cos(highlight.yaw / 2)],
                      keepOutside: true
                  }
                : undefined
        )[0]
    );
    const pointGeometry = $derived(
        new THREE.BufferGeometry()
            .setAttribute('position', new THREE.BufferAttribute(batch.positions, 3))
            .setAttribute('color', new THREE.BufferAttribute(colors, 3))
    );

    interactivity();
</script>

<T.Color attach="background" args={['#10141c']} />
<T.GridHelper args={[24, 24, '#344054', '#202938']} rotation={[Math.PI / 2, 0, 0]} />
<T.Points geometry={pointGeometry}>
    <T.PointsMaterial vertexColors size={3} sizeAttenuation={false} />
</T.Points>
<CuboidDraftTarget
    {bounds}
    {cameraMode}
    {batch}
    onHighlightChange={(box) => {
        highlight = box;
    }}
    onCreateCuboid={(box) => {
        boxes.push(box);
        onCreateCuboid?.(box);
    }}
/>
{#each boxes as box, index (index)}
    <CuboidDraftPreview {box} />
{/each}
