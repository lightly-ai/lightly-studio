<script lang="ts">
    // Stands in for SampleAnnotation so a test can fire a finished box resize.
    const { onBoundingBoxChanged }: { onBoundingBoxChanged?: (bbox: unknown) => void } = $props();
</script>

<button
    data-testid="resize-box"
    onclick={() => onBoundingBoxChanged?.({ x: 5, y: 6, width: 20, height: 21 })}
>
    resize
</button>
