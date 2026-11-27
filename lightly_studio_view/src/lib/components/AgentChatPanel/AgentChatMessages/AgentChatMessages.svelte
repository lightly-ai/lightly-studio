<script lang="ts">
    import ArrowDown from '@lucide/svelte/icons/arrow-down';
    import { Button } from '$lib/components/ui/button';
    import { tick } from 'svelte';
    import { getNextStepSuggestions } from '../nextStepSuggestions';
    import type { ChatTurn } from '../useAgentChat/chatHistory';
    import AgentTurn from './AgentTurn/AgentTurn.svelte';

    interface Props {
        turns: ChatTurn[];
        liveText: string;
        liveReasoning: string;
        isSending: boolean;
        onPick: (prompt: string) => void;
        onEdit: (prompt: string) => void;
    }

    const { turns, liveText, liveReasoning, isSending, onPick, onEdit }: Props = $props();

    const BOTTOM_THRESHOLD_PX = 24;
    let container: HTMLDivElement | undefined = $state();
    let follow = $state(true);
    let hasNewOutput = $state(false);

    function jumpToLatest() {
        if (!container) return;
        follow = true;
        hasNewOutput = false;
        container.scrollTop = container.scrollHeight;
    }

    function onScroll() {
        if (!container) return;
        follow =
            container.scrollHeight - container.clientHeight - container.scrollTop <=
            BOTTOM_THRESHOLD_PX;
        if (follow) hasNewOutput = false;
    }

    $effect(() => {
        void turns;
        void liveText;
        void liveReasoning;
        void isSending;
        void tick().then(() => {
            if (follow) jumpToLatest();
            else hasNewOutput = true;
        });
    });
</script>

<div class="relative flex min-h-0 flex-1 flex-col">
    <!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard users must be able to scroll the transcript.) -->
    <div
        bind:this={container}
        onscroll={onScroll}
        class="scrollbar-thin min-h-0 flex-1 overflow-y-auto overscroll-contain"
        role="region"
        aria-label="Conversation"
        tabindex="0"
    >
        <div class="mx-auto flex w-full max-w-2xl flex-col gap-7 px-4 py-5">
            {#each turns as turn, index (index)}
                {@const isLatest = index === turns.length - 1}
                <AgentTurn
                    {turn}
                    liveText={isLatest ? liveText : ''}
                    liveReasoning={isLatest ? liveReasoning : ''}
                    suggestions={isLatest && turn.status === 'done'
                        ? getNextStepSuggestions(turn.messages)
                        : []}
                    {onPick}
                    suggestionsDisabled={isSending}
                    {onEdit}
                />
            {/each}
        </div>
    </div>
    {#if hasNewOutput}
        <Button
            variant="outline"
            size="sm"
            class="absolute bottom-3 left-1/2 -translate-x-1/2 gap-1.5 rounded-full bg-background shadow"
            onclick={jumpToLatest}
        >
            <ArrowDown class="size-3.5" />
            Jump to latest
        </Button>
    {/if}
</div>
