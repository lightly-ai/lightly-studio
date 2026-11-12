<script lang="ts">
    import { T } from '@threlte/core';
    import type { Bounds3, CameraMode } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { PointBatch } from '$lib/components/PointCloudViewer';
    import { getCuboidCreationPlane } from './cuboidCreationPlane';
    import type { CuboidBox } from './cuboidDraft';
    import CuboidDraftPreview from './CuboidDraftPreview.svelte';
    import { useCuboidDraft } from './useCuboidDraft';

    /** Invisible plane on which the user draws a cuboid in steps. */
    interface Props {
        /** Retained bounds that keep the plane aligned with the visible ground plane. */
        bounds: Bounds3;
        /** Projection orientation used for rendering and editing. */
        cameraMode?: CameraMode;
        /** Points of the current tick, used to fit a drawn cuboid. */
        batch?: PointBatch;
        /** Timeline tick on display. A change discards the draft. */
        tick?: number;
        /**
         * Fires when the region whose points the draft takes in changes; null when there is none.
         * It does not fire when this component is destroyed, because a state write during teardown
         * stalls the update that destroys it. The owner drops the highlight with the tool instead.
         */
        onHighlightChange?: (box: CuboidBox | null) => void;
        /** Fires with the drawn box when the last step completes. */
        onCreateCuboid: (box: CuboidBox) => void;
    }

    let {
        bounds,
        cameraMode = 'perspective',
        batch,
        tick,
        onHighlightChange,
        onCreateCuboid
    }: Props = $props();
    const layout = $derived(getCuboidCreationPlane(bounds, cameraMode));
    const draft = useCuboidDraft({
        getCameraMode: () => cameraMode,
        getBatch: () => batch,
        getTick: () => tick,
        onCreate: (box) => onCreateCuboid(box)
    });

    $effect(() => {
        onHighlightChange?.(draft.highlightBox);
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
