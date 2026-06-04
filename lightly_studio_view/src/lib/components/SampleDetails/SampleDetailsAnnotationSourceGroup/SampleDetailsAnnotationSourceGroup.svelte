<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { ColorMarker } from '$lib/components/SideMenu';
    import { ChevronDown, Eye, EyeOff } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import type { Snippet } from 'svelte';
    import { slide } from 'svelte/transition';

    interface Props {
        name: string;
        count: number;
        /** Whether the group starts expanded. Captured once on mount; the chevron then
         * toggles independently of the eye. */
        initiallyOpen?: boolean;
        showColorMarker: boolean;
        allHidden: boolean;
        onToggleVisibility: (e: MouseEvent) => void;
        children: Snippet;
    }

    let {
        name,
        count,
        initiallyOpen = true,
        showColorMarker,
        allHidden,
        onToggleVisibility,
        children
    }: Props = $props();

    let open = $state(initiallyOpen);

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
                    class="size-4 transition-transform"
                    style={`transform: ${open ? 'rotate(-180deg)' : 'rotate(0deg)'}; transition-duration: ${duration}ms`}
                />
            </div>
        </CollapsibleTrigger>
        <div class="flex shrink-0 items-center">
            {#if allHidden}
                <Tooltip content="Show all annotations from this source">
                    <button
                        type="button"
                        aria-label="Show all annotations from this source"
                        class="flex items-center"
                        onclick={onToggleVisibility}
                    >
                        <EyeOff
                            data-testid="source-group-eye-off"
                            class="size-4 text-muted-foreground"
                        />
                    </button>
                </Tooltip>
            {:else}
                <Tooltip content="Hide all annotations from this source">
                    <button
                        type="button"
                        aria-label="Hide all annotations from this source"
                        class="flex items-center"
                        onclick={onToggleVisibility}
                    >
                        <Eye data-testid="source-group-eye" class="size-4" />
                    </button>
                </Tooltip>
            {/if}
        </div>
    </div>
    <CollapsibleContent forceMount>
        {#if open}
            <div class="mt-2" transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
