<script lang="ts">
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { ChevronDown } from '@lucide/svelte';
    import { untrack } from 'svelte';
    import ClassifierProcessOverview from './ClassifierProcessOverview.svelte';

    interface Props {
        phase: 'closed' | 'create' | 'refine';
        isTemporary: boolean;
    }

    let { phase, isTemporary }: Props = $props();
    let isOpen = $state(untrack(() => phase === 'create'));
    let previousPhase = $state(untrack(() => phase));
    const step = $derived(
        phase === 'create' ? 'Step 1 of 3: Choose examples' : 'Step 2 of 3: Review predictions'
    );

    $effect(() => {
        if (phase === previousPhase) return;
        isOpen = phase === 'create';
        previousPhase = phase;
    });
</script>

<Collapsible bind:open={isOpen}>
    <CollapsibleTrigger
        class="flex w-full items-center justify-between rounded-lg border bg-muted/20 px-3 py-2 text-left text-sm font-medium"
    >
        <span>{step} <span class="text-muted-foreground">— How it works</span></span>
        <ChevronDown class="size-4 transition-transform {isOpen ? 'rotate-180' : ''}" />
    </CollapsibleTrigger>
    <CollapsibleContent class="space-y-3 pt-3">
        <ClassifierProcessOverview {isTemporary} />
        {#if phase === 'refine'}
            <div class="space-y-1 text-sm text-muted-foreground">
                <p>Checked images are predicted matches.</p>
                <p>
                    Keep correct matches checked, uncheck incorrect matches, and check missed
                    matches.
                </p>
                <p>
                    Apply corrections to retrain and receive another review batch. Repeat or finish
                    whenever you are satisfied.
                </p>
            </div>
        {/if}
    </CollapsibleContent>
</Collapsible>
