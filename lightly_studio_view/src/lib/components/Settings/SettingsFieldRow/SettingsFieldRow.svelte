<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Label } from '$lib/components/ui/label';

    interface Props {
        id: string;
        label: string;
        description?: string;
        children: Snippet;
    }

    const { id, label, description, children }: Props = $props();
</script>

<div class="flex min-h-11 items-center justify-between gap-6 py-2">
    <div class="min-w-0 space-y-0.5">
        <Label for={id} class="text-sm font-normal text-foreground">
            {label}
        </Label>
        {#if description}
            <p class="text-xs text-muted-foreground">{description}</p>
        {/if}
    </div>
    <div class="shrink-0">
        {@render children()}
    </div>
</div>
