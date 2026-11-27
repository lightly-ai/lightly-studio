<script lang="ts">
    import { polygonsToSvgPath } from '../utils';

    interface Props {
        polygons: Array<Array<[number, number]>>;
        label: string;
        colorStroke: string;
        colorFill: string;
        opacity: number;
    }

    const { polygons, label, colorStroke, colorFill, opacity }: Props = $props();

    const path = $derived(polygonsToSvgPath(polygons));
</script>

<path
    d={path}
    fill-rule="nonzero"
    stroke={colorStroke}
    vector-effect="non-scaling-stroke"
    stroke-width="2"
    fill={colorFill}
    fill-opacity={opacity}
    pointer-events="all"
    aria-label={label}
    data-testid="annotation_polygon"
/>
