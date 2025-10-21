<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import type { Component, Snippet } from 'svelte';
    import { slide } from 'svelte/transition';

    let {
        title,
        icon: Icon,
        children
    }: {
        title: string;
        icon?: Component;
        children: Snippet;
    } = $props();

    let open = $state(true);

    const duration = 168; // phi
</script>

<Collapsible bind:open>
    <CollapsibleTrigger class="w-full">
        <h2 class="py-2 text-lg font-semibold">
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
    <CollapsibleContent forceMount>
        {#if open}
            <div class="mt-2" transition:slide={{ duration }}>
                {@render children()}
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
