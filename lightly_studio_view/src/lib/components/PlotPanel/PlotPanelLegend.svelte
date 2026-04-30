<script lang="ts">
    let { categoryColors }: { categoryColors: string[] } = $props();
</script>

<div
    class="absolute bottom-1 left-3 flex items-start gap-1.5 rounded-md border border-white/10 bg-black/60 px-2 py-1 text-xs text-muted-foreground backdrop-blur-sm"
    data-testid="plot-legend"
>
    <div class="flex flex-col items-start gap-1">
        <span class="flex items-center gap-1.5">
            <span class="legend-dot" style={`background-color: ${categoryColors[0]}`}></span>
            Not Filtered
        </span>
        <span class="flex items-center gap-1.5">
            <span class="legend-dot" style={`background-color: ${categoryColors[1]}`}></span>
            Filtered
        </span>
    </div>
</div>

<style>
    .legend-dot {
        display: inline-block;
        height: 0.75rem;
        width: 0.75rem;
        border-radius: 9999px;
    }
</style>
