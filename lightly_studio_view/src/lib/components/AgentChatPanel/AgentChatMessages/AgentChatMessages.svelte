<script lang="ts">
    import { tick } from 'svelte';
    import { cn } from '$lib/utils/shadcn';
    import type { toChatEntries } from '../toChatEntries';
    import AgentThinkingBlock from './AgentThinkingBlock/AgentThinkingBlock.svelte';
    import AgentToolEntry from './AgentToolEntry/AgentToolEntry.svelte';

    interface Props {
        entries: ReturnType<typeof toChatEntries>;
        /** The text of the step that the model writes now. */
        draft: { reasoning: string; content: string };
        isSending: boolean;
    }

    const { entries, draft, isSending }: Props = $props();

    let container: HTMLDivElement | undefined = $state();

    const isToolRunning = $derived(
        entries.some((entry) => entry.kind === 'tool' && entry.status === 'running')
    );
    const isWaiting = $derived(isSending && !draft.reasoning && !draft.content && !isToolRunning);

    // Keep the newest text in view.
    $effect(() => {
        void entries.length;
        void draft.reasoning;
        void draft.content;
        void isSending;
        void tick().then(() => container?.scrollTo({ top: container.scrollHeight }));
    });
</script>

{#snippet bubble(kind: 'user' | 'assistant', text: string)}
    <div
        class={cn(
            'max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm',
            kind === 'user'
                ? 'self-end bg-primary text-primary-foreground'
                : 'self-start bg-muted text-foreground'
        )}
        data-testid={`agent-chat-${kind}`}
    >
        {text}
    </div>
{/snippet}

<div bind:this={container} class="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
    {#if entries.length === 0 && !isSending}
        <p class="text-sm text-muted-foreground" data-testid="agent-chat-empty">
            Try: "Select 200 diverse but representative images" or "Find the 10 images most similar
            to a tiger and tag them tiger".
        </p>
    {/if}
    {#each entries as entry, index (index)}
        {#if entry.kind === 'tool'}
            <AgentToolEntry name={entry.name} status={entry.status} summary={entry.summary} />
        {:else if entry.kind === 'thinking'}
            <AgentThinkingBlock text={entry.text} isLive={false} />
        {:else if entry.kind === 'step'}
            <p
                class="self-start text-sm italic text-muted-foreground"
                data-testid="agent-chat-step"
            >
                {entry.text}
            </p>
        {:else}
            {@render bubble(entry.kind, entry.text)}
        {/if}
    {/each}
    {#if draft.reasoning}
        <AgentThinkingBlock text={draft.reasoning} isLive={true} />
    {/if}
    {#if draft.content}
        {@render bubble('assistant', draft.content)}
    {/if}
    {#if isWaiting}
        <p class="animate-pulse text-sm text-muted-foreground" data-testid="agent-chat-thinking">
            Thinking…
        </p>
    {/if}
</div>
