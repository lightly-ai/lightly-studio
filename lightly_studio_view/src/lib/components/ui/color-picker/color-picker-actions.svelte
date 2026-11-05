<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { RotateCcw } from '@lucide/svelte';

    interface Props {
        onApply: () => void;
        onCancel: () => void;
        onReset?: () => void;
        isDefaultColor?: boolean;
    }

    let { onApply, onCancel, onReset, isDefaultColor = false }: Props = $props();

    let applyButton = $state<HTMLButtonElement | null>(null);

    // Reset disables itself, so move focus to the next step instead of losing it.
    function handleReset(reset: () => void): void {
        reset();
        applyButton?.focus();
    }
</script>

<div class="mt-3 flex items-center gap-2">
    {#if onReset}
        <Button
            size="sm"
            variant="ghost"
            class="text-muted-foreground -ml-1.5 h-7 gap-1 px-1.5 py-0 text-xs"
            aria-label="Reset to default"
            title="Reset to default"
            disabled={isDefaultColor}
            onclick={() => handleReset(onReset)}
        >
            <RotateCcw class="size-3" />
            Reset
        </Button>
    {/if}
    <Button size="sm" variant="outline" class="ml-auto h-7 px-2 py-0 text-xs" onclick={onCancel}>
        Cancel
    </Button>
    <Button bind:ref={applyButton} size="sm" class="h-7 px-2 py-0 text-xs" onclick={onApply}>
        Apply
    </Button>
</div>
