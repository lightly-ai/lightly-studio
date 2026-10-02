<script lang="ts">
    import { Grid } from '@threlte/extras';
    import type { Bounds3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { computeGroundPlaneLayout, type GroundPlaneLayout } from './groundPlaneLayout';

    /** Renders a reference grid just below the point cloud. */
    interface Props {
        /** Bounds of the displayed point cloud. */
        pointCloudBounds: Bounds3;
    }

    let { pointCloudBounds }: Props = $props();

    const CELL_COLOR = 'hsl(20, 5%, 35%)';
    const SECTION_COLOR = 'hsl(20, 5%, 55%)';
    const CELL_SIZE = 1;
    const layout = $derived(computeGroundPlaneLayout(pointCloudBounds));
    let stableLayout = $state<GroundPlaneLayout | null>(null);

    $effect(() => {
        const currentLayout = layout;
        if (!stableLayout && currentLayout) stableLayout = currentLayout;
    });

</script>

{#if stableLayout}
    <Grid
        plane="xy"
        position={[...stableLayout.center]}
        cellColor={CELL_COLOR}
        cellSize={CELL_SIZE}
        cellThickness={0.5}
        sectionColor={SECTION_COLOR}
        sectionSize={CELL_SIZE * 10}
        sectionThickness={1}
        backgroundOpacity={0}
        infiniteGrid
        fadeOrigin={[...stableLayout.center]}
        fadeDistance={stableLayout.fadeDistance}
    />
{/if}
