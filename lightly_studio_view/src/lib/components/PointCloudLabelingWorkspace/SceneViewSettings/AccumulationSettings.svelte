<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Slider } from '$lib/components/ui/slider';

    interface Props {
        accumulatePointClouds: boolean;
        accumulationRadius: number;
        setAccumulatePointClouds: (enabled: boolean) => void;
        setAccumulationRadius: (radius: number) => void;
    }

    let {
        accumulatePointClouds,
        accumulationRadius,
        setAccumulatePointClouds,
        setAccumulationRadius
    }: Props = $props();
</script>

<div class="space-y-2 border-t pt-3">
    <label class="flex items-center gap-2 text-sm">
        <Checkbox
            aria-label="Accumulate point clouds"
            checked={accumulatePointClouds}
            onCheckedChange={(checked) => setAccumulatePointClouds(checked === true)}
        />
        <span>Accumulate point clouds</span>
    </label>
    {#if accumulatePointClouds}
        <div class="space-y-2">
            <div class="flex items-center justify-between text-sm">
                <span>Ticks on each side</span>
                <span class="tabular-nums text-muted-foreground">±{accumulationRadius} ticks</span>
            </div>
            <Slider
                type="single"
                value={accumulationRadius}
                min={1}
                max={10}
                step={1}
                aria-label="Accumulation radius"
                onValueChange={setAccumulationRadius}
            />
        </div>
    {/if}
</div>
