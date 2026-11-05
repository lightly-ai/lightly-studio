<script lang="ts">
    import { Button } from '$lib/components/ui/button';

    interface Props {
        onApply: () => void;
        onCancel: () => void;
        onReset?: () => void;
    }

    let { onApply, onCancel, onReset }: Props = $props();
</script>

<div class="mt-3 space-y-2">
    {#if onReset}
        <Button size="sm" variant="ghost" class="h-7 px-2 py-0 text-xs" onclick={onReset}>
            Reset to default
        </Button>
    {/if}
    <div class="flex justify-end gap-2">
        <Button size="sm" variant="outline" class="h-7 px-2 py-0 text-xs" onclick={onCancel}>
            Cancel
        </Button>
        <Button size="sm" class="h-7 px-2 py-0 text-xs" onclick={onApply}>Apply</Button>
    </div>
</div>
