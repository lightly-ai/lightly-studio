<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Label } from '$lib/components/ui/label';
    import { cn } from '$lib/utils';

    interface Props {
        id: string;
        label: string;
        description?: string;
        /** Whether clicking the label activates the control. */
        isLabelClickable?: boolean;
        children: Snippet;
    }

    const { id, label, description, isLabelClickable = false, children }: Props = $props();
</script>

<div class="group flex min-h-11 items-center justify-between gap-6 py-2">
    <div class="min-w-0 space-y-0.5">
        <Label
            for={id}
            class={cn(
                'text-sm font-normal text-foreground',
                isLabelClickable && 'cursor-pointer group-has-[:disabled]:cursor-default'
            )}
        >
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
