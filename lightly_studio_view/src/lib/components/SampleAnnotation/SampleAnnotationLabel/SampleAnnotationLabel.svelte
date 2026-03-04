<script lang="ts">
    import { getColorByLabel } from '$lib/utils';
    const {
        coordinates,
        colorText,
        label,
        fontSize = 14,
        isPrediction = false,
        trackId = null
    }: {
        coordinates: [number, number];
        colorText: ReturnType<typeof getColorByLabel>;
        label: string;
        fontSize?: number;
        boxGap?: number;
        isPrediction?: boolean;
        trackId?: number | null;
    } = $props();
    const displayLabel = $derived.by(() => {
        const base = isPrediction ? `${label} (pred)` : label;
        return trackId != null ? `${base} #${trackId}` : base;
    });
    const [x, y] = $derived(coordinates);
    let textElement: SVGTextElement | null = $state(null);

    const labelBox = $derived.by(() => {
        if (!textElement)
            return {
                width: 0,
                height: 0
            };

        textElement.textContent = displayLabel;
        return textElement.getBBox();
    });

    const paddingX = 5;

    // Adjust styling for prediction labels
    const labelOpacity = isPrediction ? 0.8 : 1;
    const labelFontStyle = isPrediction ? 'italic' : 'normal';
</script>

<!-- This is a tricky way to have 'unscaled components, in this case we need to have unscaled text -->
<g transform={`translate(${x}, ${y})`} class="unscaled" data-label={label}>
    <rect
        y={-labelBox?.height}
        width={labelBox?.width + paddingX * 2}
        height={labelBox?.height}
        fill={colorText.color}
        opacity={labelOpacity}
    />
    <text
        x={paddingX}
        y={-5}
        bind:this={textElement}
        class="annotation-label-text"
        data-testid="svg-annotation-text"
        fill={colorText.contrastColor}
        font-size={fontSize}
        font-style={labelFontStyle}
    >
        {displayLabel}
    </text>
</g>
