<script lang="ts">
    import AgentChatInput from '../AgentChatInput/AgentChatInput.svelte';
    import AgentChatMessages from '../AgentChatMessages/AgentChatMessages.svelte';
    import AgentChatWelcome from '../AgentChatWelcome/AgentChatWelcome.svelte';
    import type { Conversation } from '../useAgentChat/chatHistory';

    interface Props {
        active: Conversation | undefined;
        liveText: string;
        liveReasoning: string;
        isSending: boolean;
        selectedCount: number;
        setDraft: (text: string) => void;
        send: (text: string) => void;
        stop: () => void;
    }

    const {
        active,
        liveText,
        liveReasoning,
        isSending,
        selectedCount,
        setDraft,
        send,
        stop
    }: Props = $props();
    let composer: ReturnType<typeof AgentChatInput> | undefined = $state();

    export function focus() {
        composer?.focus();
    }

    function editMessage(prompt: string) {
        setDraft(prompt);
        focus();
    }
</script>

{#if active?.turns.length}
    <AgentChatMessages
        turns={active.turns}
        {liveText}
        {liveReasoning}
        {isSending}
        onPick={send}
        onEdit={editMessage}
    />
{:else}
    <AgentChatWelcome onPick={send} disabled={isSending} />
{/if}
{#if isSending && active?.turns.at(-1)?.status !== 'running'}
    <p class="px-4 pb-2 text-xs text-muted-foreground" role="status">A reply is in progress.</p>
{/if}
<AgentChatInput
    bind:this={composer}
    {isSending}
    text={active?.draft ?? ''}
    {selectedCount}
    onTextChange={setDraft}
    onSend={send}
    onStop={stop}
/>
