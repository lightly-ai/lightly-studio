<script lang="ts">
    import { untrack } from 'svelte';
    import { get } from 'svelte/store';
    import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
    import X from '@lucide/svelte/icons/x';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import AgentChatInput from './AgentChatInput/AgentChatInput.svelte';
    import AgentChatMessages from './AgentChatMessages/AgentChatMessages.svelte';
    import { applyUiActions } from './applyUiActions';
    import { toChatEntries } from './toChatEntries';
    import { useAgentChat } from './useAgentChat/useAgentChat';

    interface Props {
        collectionId: string;
        onClose: () => void;
    }

    const { collectionId: collectionIdProp, onClose }: Props = $props();

    // The layout remounts the panel when the collection changes, so the first value is final.
    const collectionId = untrack(() => collectionIdProp);

    const queryClient = useQueryClient();
    const { getSelectedSampleIds } = useGlobalStorage();
    const { updateSampleIds } = useImageFilters();
    const { loadTags, clearTagsSelected, setTagSelected } = useTags({
        collection_id: collectionId
    });

    const { messages, draft, isSending, error, send, reset } = useAgentChat({
        collectionId,
        getSelectedSampleIds: () => Array.from(get(getSelectedSampleIds(collectionId))),
        onUiActions: (actions) =>
            applyUiActions(actions, {
                showTag: async (tagId) => {
                    await loadTags();
                    clearTagsSelected();
                    setTagSelected(tagId, true);
                    updateSampleIds([]);
                    await queryClient.invalidateQueries();
                },
                showSamples: (sampleIds) => {
                    clearTagsSelected();
                    updateSampleIds(sampleIds);
                },
                refreshData: async () => {
                    await loadTags();
                    await queryClient.invalidateQueries();
                }
            })
    });

    const entries = $derived(toChatEntries($messages));
</script>

<div class="flex h-full min-w-0 flex-1 flex-col gap-3 rounded-[1vw] bg-card p-4">
    <div class="flex items-center justify-between">
        <Typography variant="h5" component="h2" className="text-foreground">AI Agent</Typography>
        <div class="flex items-center gap-1">
            <Button
                icon={RotateCcw}
                variant="ghost"
                ariaLabel="Start a new conversation"
                buttonProps={{
                    size: 'icon',
                    onclick: reset,
                    disabled: $isSending,
                    class: 'h-8 w-8',
                    'data-testid': 'agent-chat-reset'
                }}
            />
            <Button
                icon={X}
                variant="ghost"
                ariaLabel="Close agent panel"
                buttonProps={{
                    size: 'icon',
                    onclick: onClose,
                    class: 'h-8 w-8',
                    'data-testid': 'agent-chat-close'
                }}
            />
        </div>
    </div>
    <AgentChatMessages {entries} draft={$draft} isSending={$isSending} />
    {#if $error}
        <p class="text-sm text-destructive" data-testid="agent-chat-error">{$error}</p>
    {/if}
    <AgentChatInput disabled={$isSending} onSend={send} />
</div>
