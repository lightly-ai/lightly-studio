<script lang="ts">
    const {
        bbox,
        label,
        colorStroke,
        colorFill,
        opacity,
        isPrediction = false
    }: {
        bbox: [number, number, number, number];
        label: string;
        colorStroke: string;
        colorFill: string;
        opacity: number;
        annotationId: string;
        isPrediction?: boolean;
    } = $props();
    // svelte-ignore state_referenced_locally
    const [x, y, width, height] = bbox;

    // Define different styles for predictions vs. ground truth
    const strokeDashArray = $derived(isPrediction ? '5,5' : 'none');
    const strokeOpacity = $derived(isPrediction ? 0.8 : 1);
</script>

<rect
    {x}
    {y}
    {width}
    {height}
    stroke={colorStroke}
    stroke-opacity={strokeOpacity}
    stroke-dasharray={strokeDashArray}
    vector-effect="non-scaling-stroke"
    stroke-width="2"
    fill={colorFill}
    fill-opacity={opacity}
    pointer-events="all"
    aria-label={label}
    data-testid="annotation_box"
/>
