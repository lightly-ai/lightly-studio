<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { ColorMarker } from '$lib/components/SideMenu';
    import { ChevronDown } from '@lucide/svelte';
    import type { Snippet } from 'svelte';
    import { slide } from 'svelte/transition';

    interface Props {
        name: string;
        count: number;
        showColorMarker: boolean;
        children: Snippet;
    }

    let { name, count, showColorMarker, children }: Props = $props();

    let open = $state(true);

    // Collapse animation duration in ms, matching the parent Segment component.
    const duration = 168;
</script>

<Collapsible bind:open>
    <div class="flex items-center gap-2" data-testid="annotation-source-group-header" title={name}>
        {#if showColorMarker}
            <ColorMarker label={name} enableColorPicker />
        {/if}
        <CollapsibleTrigger class="flex min-w-0 flex-1 items-center justify-between py-1">
            <span class="truncate text-sm font-medium">{name}</span>
            <div class="flex shrink-0 items-center gap-2">
                <span class="text-xs text-muted-foreground">{count}</span>
                <ChevronDown
                    class="size-4 transition-transform duration-{duration}"
                    style={`transform: ${open ? 'rotate(-180deg)' : 'rotate(0deg)'}`}
                />
            </div>
        </CollapsibleTrigger>
    </div>
    <CollapsibleContent forceMount>
        {#if open}
            <div class="mt-2" transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
