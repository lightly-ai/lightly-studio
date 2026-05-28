<script lang="ts">
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { SquareCheck } from '@lucide/svelte';
    import Button from '../ui/button/button.svelte';

    const { onclick }: { onclick: () => Promise<void> } = $props();
</script>

<Tooltip content="Select all" position="bottom">
    <Button
        class="shrink-0 gap-1.5"
        data-testid="select-all-button"
        variant="toolbar"
        size="toolbar"
        aria-label="Select all"
        title="Select all"
        {onclick}
    >
        <SquareCheck class="size-4" />
        <span>Select all</span>
    </Button>
</Tooltip>
