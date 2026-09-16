<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { cn, formatInteger } from '$lib/utils';
    import { ChevronDown } from '@lucide/svelte';
    import type { Component, Snippet } from 'svelte';
    import { slide } from 'svelte/transition';
    import { getSegmentDensity } from './segmentDensity';

    let {
        title,
        icon: Icon,
        count,
        children
    }: {
        title: string;
        icon?: Component;
        /** Optional total shown on the right of the trigger, e.g. the number of rows inside. */
        count?: number;
        children: Snippet;
    } = $props();

    let open = $state(true);

    const duration = 168; // phi

    const isCompact = getSegmentDensity() === 'compact';

    // The sidebar puts the chevron before the title and rotates it a quarter turn, so a column
    // of collapsed groups reads as a list. Standalone segments keep the half-turn convention.
    const chevronRotation = $derived.by(() => {
        if (!isCompact) return open ? 'rotate(-180deg)' : 'rotate(0deg)';
        return open ? 'rotate(0deg)' : 'rotate(-90deg)';
    });
</script>

{#snippet chevron()}
    <ChevronDown
        class={cn('transition-transform', isCompact && 'size-[11px] shrink-0 opacity-55')}
        style={`transition-duration: ${duration}ms; transform: ${chevronRotation}`}
    />
{/snippet}

<Collapsible bind:open>
    <CollapsibleTrigger class={cn('w-full', isCompact && 'mt-0.5')}>
        <h2
            class={cn(
                'font-semibold',
                isCompact
                    ? 'flex h-[26px] items-center rounded-md px-2 text-[12.5px] text-diffuse-foreground hover:bg-sidebar-accent/60'
                    : 'py-2 text-base'
            )}
        >
            <div class="flex w-full min-w-0 items-center justify-between">
                <div class={cn('flex min-w-0 items-center', isCompact ? 'gap-[5px]' : 'space-x-2')}>
                    {#if isCompact}
                        {@render chevron()}
                    {/if}
                    {#if Icon}
                        <Icon />
                    {/if}
                    <span class="truncate">{title}</span>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                    {#if count !== undefined}
                        <span
                            class="text-[11px] font-normal tabular-nums text-muted-foreground"
                            data-testid="segment-count">{formatInteger(count)}</span
                        >
                    {/if}
                    {#if !isCompact}
                        {@render chevron()}
                    {/if}
                </div>
            </div>
        </h2>
    </CollapsibleTrigger>
    <CollapsibleContent forceMount>
        {#if open}
            <!-- Rows carry their own 22px indent, so the content wrapper adds none. -->
            <div class={cn(isCompact ? 'pt-0.5' : 'mt-2')} transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
