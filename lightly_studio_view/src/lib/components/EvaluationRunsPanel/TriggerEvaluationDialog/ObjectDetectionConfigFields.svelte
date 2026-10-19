<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import { Switch } from '$lib/components/ui/switch';
    import { Label } from '$lib/components/ui/label';

    interface Props {
        /** IoU threshold used to match predictions to ground truth (0–1). */
        iouThreshold: number;
        /** Whether predictions and ground truth are matched within the same class only. */
        classwise: boolean;
    }

    let { iouThreshold = $bindable(0.5), classwise = $bindable(true) }: Props = $props();
</script>

<div class="grid gap-2">
    <div class="flex items-center justify-between">
        <Label class="text-foreground">Minimum overlap (IoU)</Label>
        <span class="text-sm tabular-nums text-muted-foreground" data-testid="iou-threshold-value">
            {iouThreshold.toFixed(2)}
        </span>
    </div>
    <p class="text-xs text-muted-foreground">
        How much a prediction must overlap the ground truth to count as a match.
    </p>
    <Slider
        type="single"
        class="w-full"
        value={iouThreshold}
        min={0}
        max={1}
        step={0.05}
        onValueChange={(value: number) => (iouThreshold = value)}
        data-testid="iou-threshold-slider"
    />
    <div class="flex justify-between text-xs text-muted-foreground">
        <span>← Less overlap</span>
        <span>More overlap →</span>
    </div>
</div>

<div class="flex items-center justify-between">
    <div class="flex flex-col gap-1">
        <Label for="evaluation-classwise" class="text-foreground">Require the same class</Label>
        <p id="evaluation-classwise-description" class="text-xs text-muted-foreground">
            A predicted car must match a car.
        </p>
    </div>
    <Switch
        id="evaluation-classwise"
        aria-describedby="evaluation-classwise-description"
        bind:checked={classwise}
        data-testid="classwise-switch"
    />
</div>
