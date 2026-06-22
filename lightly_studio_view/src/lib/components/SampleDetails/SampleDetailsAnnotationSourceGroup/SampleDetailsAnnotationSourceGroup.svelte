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
        /** Whether the group starts expanded. Re-applied whenever `sampleId` changes. */
        initiallyOpen?: boolean;
        /** The sample currently shown; changing it re-applies `initiallyOpen`. */
        sampleId: string;
        showColorMarker: boolean;
        /** When omitted, the visibility eye is hidden (e.g. for classifications, which
         * are not drawn on the canvas and so cannot be toggled). */
        allHidden?: boolean;
        onToggleVisibility?: (e: MouseEvent) => void;
        children: Snippet;
    }

    let {
        name,
        count,
        initiallyOpen = true,
        sampleId,
        showColorMarker,
        allHidden = false,
        onToggleVisibility,
        children
    }: Props = $props();

    let open = $state(initiallyOpen);

    // The component is reused across samples (the parent's {#each} is keyed by source id), so
    // re-apply the seeded collapse on sample change. Tracked by sampleId so a manual toggle
    // persists within a sample and the chevron stays independent of the eye.
    let appliedSampleId = sampleId;
    $effect(() => {
        if (appliedSampleId === sampleId) return;
        appliedSampleId = sampleId;
        open = initiallyOpen;
    });

    // Collapse animation duration in ms, matching the parent Segment component.
    const duration = 168;
</script>

<Collapsible bind:open>
    <div class="flex items-center gap-2" data-testid="annotation-source-group-header" title={name}>
        {#if showColorMarker}
            <ColorMarker
                label={name}
                enableColorPicker
                markerProps={{ 'data-testid': `color-marker-${name}` }}
            />
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
        {#if onToggleVisibility}
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
        {/if}
    </div>
    <CollapsibleContent forceMount>
        {#if open}
            <div class="mt-2" transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
