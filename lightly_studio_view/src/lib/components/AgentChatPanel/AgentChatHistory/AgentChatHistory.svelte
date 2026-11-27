<script lang="ts">
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import MessageSquare from '@lucide/svelte/icons/message-square';
    import { Button } from '$lib/components/ui/button';
    import type { Conversation } from '../useAgentChat/chatHistory';

    interface Props {
        conversations: Conversation[];
        activeId: string;
        onSelect: (id: string) => void;
    }

    const { conversations, activeId, onSelect }: Props = $props();
    const dateFormat = new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short'
    });
</script>

<section class="min-h-0 flex-1 overflow-y-auto p-4" aria-label="Chat history">
    <h3 class="mb-1 text-base font-semibold">History</h3>
    <p class="mb-4 text-xs text-muted-foreground">
        Conversations in this collection are saved in this browser.
    </p>
    {#if conversations.length}
        <ul class="space-y-1">
            {#each conversations as conversation (conversation.id)}
                <li>
                    <Button
                        variant={activeId === conversation.id ? 'secondary' : 'ghost'}
                        class="h-auto w-full justify-start gap-3 px-3 py-2.5 text-left"
                        aria-current={activeId === conversation.id ? 'true' : undefined}
                        onclick={() => onSelect(conversation.id)}
                    >
                        <MessageSquare class="size-4 shrink-0 text-muted-foreground" />
                        <span class="min-w-0 flex-1">
                            <span class="block truncate" title={conversation.turns[0].prompt}>
                                {conversation.turns[0].prompt}
                            </span>
                            <time
                                class="block text-xs font-normal text-muted-foreground"
                                datetime={new Date(conversation.updatedAt).toISOString()}
                            >
                                {dateFormat.format(conversation.updatedAt)}
                            </time>
                        </span>
                        <ChevronRight class="size-4 shrink-0 text-muted-foreground" />
                    </Button>
                </li>
            {/each}
        </ul>
    {:else}
        <p class="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
            Your conversations will appear here after you send a message.
        </p>
    {/if}
</section>
