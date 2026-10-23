<script lang="ts">
    import type { SmartSelectPoint } from './SmartSelectOverlay.helpers';

    interface Props {
        points: SmartSelectPoint[];
        image: { width: number; height: number };
        // Screen pixels per image pixel, so the markers keep their size when zooming.
        scale: number;
    }

    let { points, image, scale }: Props = $props();
</script>

{#each points as point, index (index)}
    <g
        transform={`translate(${point.x * image.width} ${point.y * image.height})`}
        pointer-events="none"
        data-testid={point.positive ? 'smart-select-positive-point' : 'smart-select-negative-point'}
    >
        <circle
            r={9 / scale}
            fill="rgba(15, 23, 42, 0.9)"
            stroke="white"
            stroke-width={2 / scale}
        />
        <circle
            r={6 / scale}
            fill={point.positive ? '#10b981' : '#f43f5e'}
            stroke={point.positive ? '#a7f3d0' : '#fecdd3'}
            stroke-width={1.5 / scale}
        />
        <text
            text-anchor="middle"
            dominant-baseline="central"
            fill="white"
            font-size={9 / scale}
            font-weight="700">{point.positive ? '+' : '-'}</text
        >
    </g>
{/each}
