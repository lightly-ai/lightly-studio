<script lang="ts">
    import { Canvas } from '@threlte/core';
    import PointCloudScene from './PointCloudScene.svelte';
    import type { ColorMode } from './pointCloudUtils';
    import type { PointBatch } from './pointCloudBuffer';

    interface Props {
        /** A single point cloud batch to render. */
        batch: PointBatch;
        /** Color mapping mode. "none" uses a neutral gray, "intensity" maps point intensity to color, "height" maps Z-axis to color. */
        colorMode?: ColorMode;
        /** Size of each rendered point. */
        pointSize?: number;
        /** Optional [min, max] range for intensity normalization. Auto-normalizes from data if omitted. */
        intensityRange?: [number, number];
    }

    let { batch, colorMode = 'none', pointSize = 2, intensityRange }: Props = $props();
</script>

<div class="h-full w-full">
    <Canvas>
        <PointCloudScene {batch} {colorMode} {pointSize} {intensityRange} />
    </Canvas>
</div>
