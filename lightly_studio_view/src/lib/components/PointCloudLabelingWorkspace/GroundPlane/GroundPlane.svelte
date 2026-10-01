<script lang="ts">
    import { useTask, useThrelte } from '@threlte/core';
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
    const { camera } = useThrelte();
    const layout = $derived(computeGroundPlaneLayout(pointCloudBounds));
    let stableLayout = $state<GroundPlaneLayout | null>(null);
    let cellSize = $state(1);

    $effect(() => {
        const currentLayout = layout;
        if (!stableLayout && currentLayout) stableLayout = currentLayout;
    });

    useTask(
        () => {
            if (!stableLayout) return;
            const [x, y, z] = stableLayout.center;
            const position = camera.current.position;
            const distance = Math.hypot(position.x - x, position.y - y, position.z - z);
            const nextCellSize = getGridCellSize(distance);
            if (nextCellSize !== cellSize) cellSize = nextCellSize;
        },
        { autoInvalidate: false }
    );

    function getGridCellSize(distance: number): number {
        const target = Math.max(distance * 0.075, 0.000001);
        const magnitude = 10 ** Math.floor(Math.log10(target));
        const normalized = target / magnitude;
        return (normalized >= 5 ? 5 : normalized >= 2 ? 2 : 1) * magnitude;
    }
</script>

{#if stableLayout}
    <Grid
        plane="xy"
        position={[...stableLayout.center]}
        cellColor={CELL_COLOR}
        {cellSize}
        cellThickness={0.5}
        sectionColor={SECTION_COLOR}
        sectionSize={cellSize * 10}
        sectionThickness={1}
        backgroundOpacity={0}
        infiniteGrid
        fadeOrigin={[...stableLayout.center]}
        fadeDistance={stableLayout.fadeDistance}
    />
{/if}
