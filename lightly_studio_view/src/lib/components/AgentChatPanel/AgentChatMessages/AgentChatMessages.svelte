<script lang="ts">
    import { tick } from 'svelte';
    import { Wrench } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn';
    import type { toChatEntries } from '../toChatEntries';

    interface Props {
        entries: ReturnType<typeof toChatEntries>;
        isSending: boolean;
    }

    const { entries, isSending }: Props = $props();

    let container: HTMLDivElement | undefined = $state();

    // Keep the newest message in view.
    $effect(() => {
        void entries.length;
        void isSending;
        void tick().then(() => container?.scrollTo({ top: container.scrollHeight }));
    });
</script>

<div bind:this={container} class="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
    {#if entries.length === 0}
        <p class="text-sm text-muted-foreground" data-testid="agent-chat-empty">
            Try: "Find the 10 images most similar to a tiger and tag them tiger" or "Select the 128
            most diverse images".
        </p>
    {/if}
    {#each entries as entry, index (index)}
        {#if entry.kind === 'tool'}
            <div
                class={cn(
                    'flex items-center gap-1.5 self-start rounded-md bg-muted px-2 py-1 text-xs',
                    entry.isError ? 'text-destructive' : 'text-muted-foreground'
                )}
                data-testid="agent-chat-tool"
            >
                <Wrench class="size-3 shrink-0" />
                <span class="font-mono">{entry.name}</span>
                <span>·</span>
                <span>{entry.summary}</span>
            </div>
        {:else}
            <div
                class={cn(
                    'max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm',
                    entry.kind === 'user'
                        ? 'self-end bg-primary text-primary-foreground'
                        : 'self-start bg-muted text-foreground'
                )}
                data-testid={`agent-chat-${entry.kind}`}
            >
                {entry.text}
            </div>
        {/if}
    {/each}
    {#if isSending}
        <p class="animate-pulse text-sm text-muted-foreground" data-testid="agent-chat-thinking">
            Thinking…
        </p>
    {/if}
</div>
