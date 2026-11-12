<script lang="ts">
    import { T } from '@threlte/core';
    import type { Bounds3, CameraMode } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { PointBatch } from '$lib/components/PointCloudViewer';
    import { getCuboidCreationPlane } from '../GroundPlane/GroundPlaneClickTarget/cuboidCreationPlane';
    import type { CuboidPlacement } from './cuboidDraft';
    import CuboidDraftPreview from './CuboidDraftPreview.svelte';
    import { useCuboidDraft } from './useCuboidDraft';

    /** Invisible plane that turns a click or drag into a cuboid placement. */
    interface Props {
        /** Retained bounds that keep the plane aligned with the visible ground plane. */
        bounds: Bounds3;
        /** Projection orientation used for rendering and editing. */
        cameraMode?: CameraMode;
        /** Points of the current tick, used to fit a drawn cuboid. */
        batch?: PointBatch;
        /** Fires with the placement when a click or drag completes. */
        onCreateCuboid: (placement: CuboidPlacement) => void;
    }

    let { bounds, cameraMode = 'perspective', batch, onCreateCuboid }: Props = $props();
    const layout = $derived(getCuboidCreationPlane(bounds, cameraMode));
    const draft = useCuboidDraft({
        getCameraMode: () => cameraMode,
        getBatch: () => batch,
        onCreate: (placement) => onCreateCuboid(placement)
    });
</script>

{#if layout}
    <T.Mesh
        position={[...layout.center]}
        rotation={[...layout.rotation]}
        visible={false}
        onpointerdown={draft.handlePlanePointerDown}
    >
        <T.PlaneGeometry args={[layout.size, layout.size]} />
        <T.MeshBasicMaterial />
    </T.Mesh>
{/if}

{#if draft.previewBox}
    <CuboidDraftPreview box={draft.previewBox} />
{/if}
