<script lang="ts">
    import { tick, untrack } from 'svelte';
    import { get } from 'svelte/store';
    import AgentChatHeader from './AgentChatHeader/AgentChatHeader.svelte';
    import AgentChatHistory from './AgentChatHistory/AgentChatHistory.svelte';
    import AgentChatConversation from './AgentChatConversation/AgentChatConversation.svelte';
    import { useAgentChat } from './useAgentChat/useAgentChat';
    import { useAgentGrid } from './useAgentGrid';

    interface Props {
        collectionId: string;
        collectionName: string;
        onClose: () => void;
    }

    const { collectionId: collectionIdProp, collectionName, onClose }: Props = $props();
    // The layout remounts the panel when the collection changes.
    const collectionId = untrack(() => collectionIdProp);
    const { selectedSamples, onUiActions } = useAgentGrid(collectionId);
    const {
        active,
        activeId,
        history,
        isLoading,
        isSending,
        liveReply,
        storageError,
        newChat,
        select,
        setDraft,
        send,
        stop
    } = useAgentChat({
        collectionId,
        getSelectedSampleIds: () => Array.from(get(selectedSamples)),
        onUiActions
    });

    let showHistory = $state(false);
    let conversation: ReturnType<typeof AgentChatConversation> | undefined = $state();

    async function focusComposer() {
        showHistory = false;
        await tick();
        conversation?.focus();
    }

    function toggleHistory() {
        if (showHistory) void focusComposer();
        else showHistory = true;
    }

    function startConversation() {
        if (!$isLoading) newChat();
        void focusComposer();
    }

    function openConversation(id: string) {
        select(id);
        void focusComposer();
    }
</script>

<aside
    class="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-border/70 bg-card text-card-foreground"
    aria-label="AI Agent"
>
    <AgentChatHeader
        {collectionName}
        {showHistory}
        onToggleHistory={toggleHistory}
        onNewChat={startConversation}
        {onClose}
    />
    {#if $storageError}
        <p class="border-b border-border/70 px-4 py-2 text-xs text-destructive" role="status">
            {$storageError}
        </p>
    {/if}
    {#if $isLoading}
        <p class="p-4 text-sm text-muted-foreground" role="status">Opening chat…</p>
    {:else if showHistory}
        <AgentChatHistory
            conversations={$history}
            activeId={$activeId}
            onSelect={openConversation}
        />
    {:else}
        {#key $activeId}
            <AgentChatConversation
                bind:this={conversation}
                active={$active}
                liveText={$liveReply?.id === $activeId ? $liveReply.text : ''}
                liveReasoning={$liveReply?.id === $activeId ? $liveReply.reasoning : ''}
                isSending={$isSending}
                selectedCount={$selectedSamples.size}
                {setDraft}
                {send}
                {stop}
            />
        {/key}
    {/if}
</aside>
