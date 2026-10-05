<script lang="ts">
    let {
        position,
        cellSize,
        fadeDistance
    }: { position: number[]; cellSize: number; fadeDistance: number } = $props();
</script>

<div
    data-testid="ground-grid"
    data-position={position.join(',')}
    data-cell-size={cellSize}
    data-fade-distance={fadeDistance}
></div>
