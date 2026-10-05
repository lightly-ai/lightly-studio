import { agentChat } from '$lib/api/lightly_studio_local/sdk.gen';
import type { AgentMessageOutput, AgentTurnResult } from '$lib/api/lightly_studio_local/types.gen';
import { derived, get, readonly, writable } from 'svelte/store';

interface UseAgentChatParams {
    collectionId: string;
    /** Reads the samples that the user selected in the grid, at send time. */
    getSelectedSampleIds: () => string[];
    /** Applies the GUI actions of a finished turn. */
    onUiActions: (actions: AgentTurnResult['ui_actions']) => Promise<void>;
}

// The transcripts outlive the panel, so closing and opening it keeps the conversation.
const transcriptsByCollection = writable<Record<string, AgentMessageOutput[]>>({});

export function useAgentChat({
    collectionId,
    getSelectedSampleIds,
    onUiActions
}: UseAgentChatParams) {
    const isSending = writable(false);
    const error = writable<string | null>(null);
    const messages = derived(
        transcriptsByCollection,
        ($transcripts) => $transcripts[collectionId] ?? []
    );

    const setTranscript = (transcript: AgentMessageOutput[]) => {
        transcriptsByCollection.update((all) => ({ ...all, [collectionId]: transcript }));
    };

    const send = async (text: string) => {
        const content = text.trim();
        if (!content || get(isSending)) return;
        const transcript = [...get(messages), { role: 'user' as const, content }];
        setTranscript(transcript);
        isSending.set(true);
        error.set(null);
        try {
            const response = await agentChat({
                path: { collection_id: collectionId },
                body: { messages: transcript, selected_sample_ids: getSelectedSampleIds() }
            });
            if (!response.data) {
                error.set(readErrorDetail(response.error));
                return;
            }
            setTranscript([...transcript, ...response.data.messages]);
            await onUiActions(response.data.ui_actions);
        } catch (err) {
            error.set(err instanceof Error ? err.message : String(err));
        } finally {
            isSending.set(false);
        }
    };

    const reset = () => {
        setTranscript([]);
        error.set(null);
    };

    return {
        messages,
        isSending: readonly(isSending),
        error: readonly(error),
        send,
        reset
    };
}

function readErrorDetail(error: unknown): string {
    const detail = (error as { detail?: unknown } | undefined)?.detail;
    return typeof detail === 'string' ? detail : 'The agent request failed.';
}
