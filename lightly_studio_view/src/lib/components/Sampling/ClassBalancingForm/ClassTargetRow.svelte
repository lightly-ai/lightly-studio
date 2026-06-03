<script lang="ts">
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';

    interface Props {
        labelName: string;
        target: number;
        onTargetChange: (labelName: string, target: number) => void;
        onRemove: (labelName: string) => void;
    }

    let { labelName, target, onTargetChange, onRemove }: Props = $props();
</script>

<div
    class="grid grid-cols-[1fr_120px_auto] gap-2"
    data-testid={`sampling-class-target-row-${labelName}`}
>
    <Label
        class="flex items-center px-3 text-sm font-medium"
        for={`sampling-class-target-${labelName}`}
    >
        {labelName}
    </Label>
    <Input
        id={`sampling-class-target-${labelName}`}
        type="number"
        min="0"
        step="1"
        value={target}
        oninput={(event) => {
            const value = (event.currentTarget as HTMLInputElement).value;
            if (value === '') return;
            onTargetChange(labelName, Number(value));
        }}
        data-testid={`sampling-class-target-input-${labelName}`}
    />
    <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={`Remove class ${labelName}`}
        onclick={() => onRemove(labelName)}
        data-testid={`sampling-class-target-remove-${labelName}`}
    >
        <Trash2 class="size-4" />
    </Button>
</div>
