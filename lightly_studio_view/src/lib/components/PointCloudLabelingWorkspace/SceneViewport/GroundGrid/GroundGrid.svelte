<script lang="ts">
    import { Grid } from '@threlte/extras';

    /**
     * Ground plane grid at z = 0 of the scene frame, which is z-up.
     *
     * Draws a line every `cellSize` meters and a stronger line every `sectionSize` meters. The
     * grid has no end and fades out with the distance to the camera, so it covers the scene in
     * every frame, e.g. the world frame, where the vehicle is far from the origin.
     */
    interface Props {
        /** Distance between two grid lines, in meters. */
        cellSize?: number;
        /** Distance between two stronger grid lines, in meters. */
        sectionSize?: number;
        /** Distance to the camera at which the grid is faded out, in meters. */
        fadeDistance?: number;
    }

    let { cellSize = 1, sectionSize = 10, fadeDistance = 200 }: Props = $props();
</script>

<Grid
    plane="xy"
    infiniteGrid
    {cellSize}
    {sectionSize}
    {fadeDistance}
    cellColor="#3f3f46"
    cellThickness={0.6}
    sectionColor="#71717a"
    sectionThickness={1}
    renderOrder={-1}
/>
