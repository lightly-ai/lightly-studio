<script lang="ts">
    import { Slider } from '$lib/components/ui/slider';

    interface Props {
        pointSize: number;
        disabled: boolean;
        onPointSizeChange: (pointSize: number) => void;
    }

    let { pointSize, disabled, onPointSizeChange }: Props = $props();
</script>

<div class="space-y-2 border-t pt-3">
    <div class="flex items-center justify-between text-sm">
        <span>Point size</span>
        <span class="tabular-nums text-muted-foreground">{pointSize}</span>
    </div>
    <Slider
        type="single"
        value={pointSize}
        min={1}
        max={10}
        step={0.5}
        {disabled}
        aria-label="Point size"
        onValueChange={onPointSizeChange}
    />
</div>
