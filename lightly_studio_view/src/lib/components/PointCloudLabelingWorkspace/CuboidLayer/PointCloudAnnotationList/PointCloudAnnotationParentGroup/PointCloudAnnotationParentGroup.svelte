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
        /** Display name of the annotation class for this group's root. */
        className: string;
        /** Track number of the root annotation; omitted from the label when null. */
        trackNumber: number | null;
        /** Total annotations in this subtree, including the root. */
        subtreeSize: number;
        /** Annotation rows rendered inside the group body. */
        children: Snippet;
    }

    let { className, trackNumber, subtreeSize, children }: Props = $props();

    const label = $derived(trackNumber !== null ? `${className} #${trackNumber}` : className);

    let open = $state(true);
    const duration = 168;
</script>

<Collapsible bind:open>
    <CollapsibleTrigger
        class="flex w-full items-center justify-between py-0.5 pb-2"
        data-testid="point-cloud-annotation-parent-group-header"
    >
        <h3 class="truncate text-xs font-medium text-muted-foreground">{label}</h3>
        <div class="flex shrink-0 items-center gap-2">
            <span class="text-xs text-muted-foreground">{subtreeSize}</span>
            <ChevronDown
                class="size-3 text-muted-foreground transition-transform"
                style={`transform: ${open ? 'rotate(-180deg)' : 'rotate(0deg)'}; transition-duration: ${duration}ms`}
            />
        </div>
    </CollapsibleTrigger>
    <CollapsibleContent forceMount>
        {#if open}
            <div transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
