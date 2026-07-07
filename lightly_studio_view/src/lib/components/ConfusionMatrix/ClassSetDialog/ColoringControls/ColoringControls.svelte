<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Slider } from '$lib/components/ui/slider';
    import type { ColorConfig } from '../types';

    let { intensity = $bindable(), logScale = $bindable() }: ColorConfig = $props();
</script>

<div class="space-y-3 border-t pt-3">
    <div class="text-sm font-medium">Coloring</div>
    <div>
        <div class="mb-2 flex items-center justify-between">
            <span class="text-xs text-muted-foreground">Color intensity</span>
            <span class="text-xs tabular-nums text-muted-foreground">
                {intensity.toFixed(1)}×
            </span>
        </div>
        <Slider
            type="single"
            bind:value={intensity}
            min={0.2}
            max={3}
            step={0.1}
            data-testid="color-intensity-slider"
        />
    </div>
    <label class="flex items-center gap-2 text-sm">
        <Checkbox bind:checked={logScale} data-testid="color-log-scale-checkbox" />
        <div class="flex flex-col">
            Logarithmic coloring
            <span class="text-xs text-muted-foreground">
                (keeps small counts visible next to large ones)
            </span>
        </div>
    </label>
</div>
