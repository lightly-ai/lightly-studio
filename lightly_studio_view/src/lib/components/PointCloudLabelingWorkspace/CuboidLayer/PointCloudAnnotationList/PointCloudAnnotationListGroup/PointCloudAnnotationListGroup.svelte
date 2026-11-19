<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import { AnnotationTargetRadio } from '$lib/components/AnnotationSource';
    import { slide } from 'svelte/transition';
    import type { Snippet } from 'svelte';
    import AnnotationVisibilityButton from '../AnnotationVisibilityButton';

    interface Props {
        /** Display name of the annotation source group. */
        name: string;
        /** Number of annotations in the group. */
        count: number;
        /** When this value changes to a new truthy string, the group auto-expands. */
        autoExpandForId?: string | null;
        /** Whether the source is hidden in the scene. */
        isHidden?: boolean;
        /** Hides or shows the source; the eye button is omitted without it. */
        onToggleVisibility?: () => void;
        /** Annotation rows rendered inside the collapsible body. */
        children: Snippet;
        /** Whether new cuboids go to this source. */
        isTarget?: boolean;
        /** Whether no source is picked yet, so the radio asks for a click. */
        needsPick?: boolean;
        /** Picks this source for new cuboids. Without it, the group has no radio. */
        onPick?: () => void;
    }

    let {
        name,
        count,
        autoExpandForId = null,
        isHidden = false,
        onToggleVisibility,
        children,
        isTarget = false,
        needsPick = false,
        onPick
    }: Props = $props();

    let open = $state(true);

    $effect(() => {
        if (autoExpandForId) {
            open = true;
        }
    });
    const duration = 168;
</script>

<Collapsible bind:open>
    <div class="flex items-center gap-1">
        {#if onPick}
            <AnnotationTargetRadio sourceName={name} {isTarget} {needsPick} onSetTarget={onPick} />
        {/if}
        <CollapsibleTrigger
            class="flex min-w-0 flex-1 items-center justify-between py-1"
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
        {#if onToggleVisibility}
            <AnnotationVisibilityButton noun="source" {isHidden} onToggle={onToggleVisibility} />
        {/if}
    </div>
    <CollapsibleContent forceMount>
        {#if open}
            <div class="mt-1" transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
