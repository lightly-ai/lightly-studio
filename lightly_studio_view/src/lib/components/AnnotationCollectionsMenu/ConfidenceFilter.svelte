<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Slider } from '$lib/components/ui/slider';
    import { useAnnotationConfidence } from '$lib/hooks/useAnnotationConfidence';

    const { minimumConfidence } = useAnnotationConfidence();
</script>

<Segment title="Confidence">
    <div class="space-y-3">
        <div class="flex justify-between text-sm">
            <span>Minimum</span>
            <span>{$minimumConfidence.toFixed(2)}</span>
        </div>
        <Slider
            type="single"
            min={0}
            max={100}
            step={1}
            value={$minimumConfidence * 100}
            onValueChange={(value) => minimumConfidence.set(value / 100)}
            aria-label="Minimum annotation confidence"
        />
        <p class="text-xs text-diffuse-foreground">Hidden annotations are still exported.</p>
    </div>
</Segment>
