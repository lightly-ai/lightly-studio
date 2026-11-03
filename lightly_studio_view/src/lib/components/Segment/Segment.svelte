<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { ChevronDown } from '@lucide/svelte';
    import type { Component, Snippet } from 'svelte';
    import { slide } from 'svelte/transition';

    let {
        title,
        icon: Icon,
        children,
        headerAction
    }: {
        title: string;
        icon?: Component;
        children: Snippet;
        /** A control next to the title, outside the collapse trigger. */
        headerAction?: Snippet;
    } = $props();

    let open = $state(true);

    const duration = 168; // phi
</script>

<Collapsible bind:open>
    <div class="flex items-center gap-1">
        <CollapsibleTrigger class="min-w-0 flex-1">
            <h2 class="py-2 text-base font-semibold">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                        {#if Icon}
                            <Icon />
                        {/if}
                        <span>{title}</span>
                    </div>
                    <div>
                        <ChevronDown
                            class="transition-transform duration-{duration}"
                            style={`transform: ${open ? 'rotate(-180deg)' : 'rotate(0deg)'}`}
                        />
                    </div>
                </div>
            </h2>
        </CollapsibleTrigger>
        {#if headerAction}
            {@render headerAction()}
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
