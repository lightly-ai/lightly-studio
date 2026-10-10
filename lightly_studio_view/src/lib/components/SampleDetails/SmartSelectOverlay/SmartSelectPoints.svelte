<script lang="ts">
    import type { SmartSelectPoint } from './SmartSelectOverlay.helpers';

    interface Props {
        points: SmartSelectPoint[];
        image: { width: number; height: number };
    }

    let { points, image }: Props = $props();
</script>

{#each points as point, index (index)}
    <g
        transform={`translate(${point.x * image.width} ${point.y * image.height})`}
        pointer-events="none"
        data-testid={point.positive ? 'smart-select-positive-point' : 'smart-select-negative-point'}
    >
        <circle
            r={Math.max(9, image.width / 170)}
            fill="rgba(15, 23, 42, 0.9)"
            stroke="white"
            stroke-width="2"
        />
        <circle
            r={Math.max(6, image.width / 240)}
            fill={point.positive ? '#10b981' : '#f43f5e'}
            stroke={point.positive ? '#a7f3d0' : '#fecdd3'}
            stroke-width="1.5"
        />
        <text
            text-anchor="middle"
            dominant-baseline="central"
            fill="white"
            font-size={Math.max(9, image.width / 260)}
            font-weight="700">{point.positive ? '+' : '-'}</text
        >
    </g>
{/each}
