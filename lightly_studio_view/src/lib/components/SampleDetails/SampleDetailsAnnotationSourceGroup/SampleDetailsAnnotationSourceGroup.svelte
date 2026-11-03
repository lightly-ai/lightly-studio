<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { ColorMarker } from '$lib/components/SideMenu';
    import { ChevronDown, Eye, EyeOff } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { untrack, type Snippet } from 'svelte';
    import { slide } from 'svelte/transition';
    import { cn } from '$lib/utils';

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
        /** Called when the user expands or collapses the group. */
        onOpenChange?: (open: boolean) => void;
        /** Rendered at the start of the header, e.g. the button that makes this the target. */
        leading?: Snippet;
        /** Tints the header, e.g. for the source new annotations go to. */
        highlighted?: boolean;
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
        onOpenChange,
        leading,
        highlighted = false,
        children
    }: Props = $props();

    let open = $state(untrack(() => initiallyOpen));

    // The component is reused across samples (the parent's {#each} is keyed by source id), so
    // re-apply the seeded collapse on sample change. Tracked by sampleId so a manual toggle
    // persists within a sample and the chevron stays independent of the eye. An empty group
    // starts collapsed, so it is also re-applied when its first annotation arrives.
    let appliedSampleId = $state(untrack(() => sampleId));
    let wasEmpty = $state(untrack(() => count === 0));
    $effect(() => {
        const isEmpty = count === 0;
        const gotFirstAnnotation = wasEmpty && !isEmpty;
        wasEmpty = isEmpty;
        if (appliedSampleId === sampleId && !gotFirstAnnotation) return;
        appliedSampleId = sampleId;
        open = initiallyOpen;
    });

    // Collapse animation duration in ms, matching the parent Segment component.
    const duration = 168;
</script>

<Collapsible bind:open {onOpenChange}>
    <div
        class={cn(
            '-mx-1 flex items-center gap-2 rounded-md px-1',
            highlighted && 'bg-primary/10 ring-1 ring-primary/40'
        )}
        data-testid="annotation-source-group-header"
        title={name}
    >
        {@render leading?.()}
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
