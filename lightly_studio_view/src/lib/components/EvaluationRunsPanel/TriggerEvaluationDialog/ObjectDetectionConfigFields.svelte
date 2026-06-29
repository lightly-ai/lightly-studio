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
        <Label class="text-foreground">IoU threshold</Label>
        <span class="text-sm tabular-nums text-muted-foreground" data-testid="iou-threshold-value">
            {iouThreshold.toFixed(2)}
        </span>
    </div>
    <Slider
        type="multiple"
        class="w-full"
        value={[iouThreshold]}
        min={0}
        max={1}
        step={0.05}
        onValueChange={(values: number[]) => (iouThreshold = values[0])}
        data-testid="iou-threshold-slider"
    />
</div>

<div class="flex items-center justify-between">
    <div class="flex flex-col gap-0.5">
        <Label class="text-foreground">Class-wise matching</Label>
        <span class="text-xs text-muted-foreground">
            Match predictions and ground truth within the same class only.
        </span>
    </div>
    <Switch bind:checked={classwise} data-testid="classwise-switch" />
</div>
