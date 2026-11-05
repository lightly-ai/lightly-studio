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
        /** A short line under the name, e.g. "New annotations go here". */
        subtitle?: string;
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
        subtitle,
        children
    }: Props = $props();

    let open = $state(untrack(() => initiallyOpen));

    // Bookkeeping for the effect below. Plain variables, so writing them doesn't re-run it.
    let appliedSampleId = untrack(() => sampleId);
    let wasEmpty = untrack(() => count === 0);

    // The component is reused across samples (the parent's {#each} is keyed by source id), so the
    // seeded collapse is re-applied on sample change. An empty group starts collapsed, so it is
    // also re-applied when its first annotation arrives. Otherwise a manual toggle persists within
    // a sample.
    $effect(() => {
        const isEmpty = count === 0;
        const gotFirstAnnotation = wasEmpty && !isEmpty;
        const isNewSample = appliedSampleId !== sampleId;
        wasEmpty = isEmpty;
        appliedSampleId = sampleId;
        if (isNewSample || gotFirstAnnotation) {
            open = initiallyOpen;
        }
    });

    // Collapse animation duration in ms, matching the parent Segment component.
    const duration = 168;

    const setOpen = (next: boolean) => {
        open = next;
        onOpenChange?.(next);
    };
</script>

<Collapsible bind:open={() => open, setOpen}>
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
            <span class="flex min-w-0 flex-col items-start">
                <span class="max-w-full truncate text-sm font-medium">{name}</span>
                {#if subtitle}
                    <span
                        class="text-xs text-primary"
                        data-testid="annotation-source-group-subtitle">{subtitle}</span
                    >
                {/if}
            </span>
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
