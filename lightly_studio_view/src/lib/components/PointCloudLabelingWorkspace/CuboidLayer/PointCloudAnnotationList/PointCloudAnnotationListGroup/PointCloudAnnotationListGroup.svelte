<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { ChevronDown } from '@lucide/svelte';
    import { slide } from 'svelte/transition';
    import type { Snippet } from 'svelte';

    interface Props {
        /** Display name of the annotation source group. */
        name: string;
        /** Number of annotations in the group. */
        count: number;
        /** Annotation rows rendered inside the collapsible body. */
        children: Snippet;
    }

    let { name, count, children }: Props = $props();

    let open = $state(true);
    const duration = 168;
</script>

<Collapsible bind:open>
    <CollapsibleTrigger
        class="flex w-full items-center justify-between py-1"
        data-testid="point-cloud-annotation-list-group-header"
    >
        <span class="truncate text-sm font-medium">{name}</span>
        <div class="flex shrink-0 items-center gap-2">
            <span class="text-xs text-muted-foreground">{count}</span>
            <ChevronDown
                class="size-4 transition-transform"
                style={`transform: ${open ? 'rotate(-180deg)' : 'rotate(0deg)'}; transition-duration: ${duration}ms`}
            />
        </div>
    </CollapsibleTrigger>
    <CollapsibleContent forceMount>
        {#if open}
            <div class="mt-1" transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
