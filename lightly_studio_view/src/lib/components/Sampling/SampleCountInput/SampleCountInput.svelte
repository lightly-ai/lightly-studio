<script lang="ts">
    import { Input } from '$lib/components/ui/input';

    interface Props {
        count: number | null;
        percentage: number | null;
        onCountChange: (value: number) => void;
        onPercentageChange: (value: number) => void;
    }

    const { count, percentage, onCountChange, onPercentageChange }: Props = $props();
</script>

<div class="flex gap-2">
    <Input
        id="n-samples"
        type="number"
        value={count ?? ''}
        oninput={(e) => onCountChange((e.target as HTMLInputElement).valueAsNumber)}
        min="1"
        placeholder="Enter the number of samples"
        required
        class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        data-testid="sampling-dialog-n-samples-input"
    />
    <div class="relative flex items-center">
        <Input
            id="n-samples-percentage"
            type="number"
            aria-label="Percentage of filtered samples"
            value={percentage ?? ''}
            oninput={(e) => onPercentageChange((e.target as HTMLInputElement).valueAsNumber)}
            min="0"
            step="any"
            placeholder="%"
            class="w-24 pr-6 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
            data-testid="sampling-dialog-n-samples-percentage-input"
        />
        <span class="pointer-events-none absolute right-2 text-sm text-muted-foreground">%</span>
    </div>
</div>
