<script lang="ts">
    import { useTask, useThrelte } from '@threlte/core';
    import { Grid } from '@threlte/extras';
    import type { Bounds3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { computeGroundPlaneLayout, getGridCellSize } from './groundPlaneLayout';

    /** Renders a reference grid just below the point cloud. */
    interface Props {
        /** Bounds of the displayed point cloud. */
        pointCloudBounds: Bounds3;
    }

    let { pointCloudBounds }: Props = $props();

    const CELL_COLOR = 'hsl(20, 5%, 35%)';
    const SECTION_COLOR = 'hsl(20, 5%, 55%)';
    const layout = $derived(computeGroundPlaneLayout(pointCloudBounds));
    const { camera } = useThrelte();
    let cellSize = $state(1);

    useTask(
        () => {
            if (!layout) return;
            const [x, y, z] = layout.center;
            const position = camera.current.position;
            const distance = Math.hypot(position.x - x, position.y - y, position.z - z);
            cellSize = getGridCellSize(distance);
        },
        { autoInvalidate: false }
    );
</script>

{#if layout}
    <Grid
        plane="xy"
        position={[...layout.center]}
        cellColor={CELL_COLOR}
        {cellSize}
        cellThickness={0.5}
        sectionColor={SECTION_COLOR}
        sectionSize={cellSize * 10}
        sectionThickness={1}
        backgroundOpacity={0}
        infiniteGrid
        fadeOrigin={[...layout.center]}
        fadeDistance={layout.fadeDistance}
    />
{/if}
