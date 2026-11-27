import { client } from '$lib/api/lightly_studio_local/client.gen';
import type { AgentMessage, TurnDoneEvent } from '$lib/api/lightly_studio_local/types.gen';
import { derived, get, readonly, writable } from 'svelte/store';
import { applyEvent, dropIncompleteStep, EMPTY_LIVE_TURN } from './liveTurn';
import { readAgentStream } from './readAgentStream';

type UiActions = TurnDoneEvent['ui_actions'];

interface UseAgentChatParams {
    collectionId: string;
    /** Reads the samples that the user selected in the grid, at send time. */
    getSelectedSampleIds: () => string[];
    /** Applies the GUI actions of a finished turn. */
    onUiActions: (actions: UiActions) => Promise<void>;
}

// The transcripts outlive the panel, so closing and opening it keeps the conversation.
const transcriptsByCollection = writable<Record<string, AgentMessage[]>>({});

export function useAgentChat({
    collectionId,
    getSelectedSampleIds,
    onUiActions
}: UseAgentChatParams) {
    const isSending = writable(false);
    const error = writable<string | null>(null);
    const liveTurn = writable(EMPTY_LIVE_TURN);
    const transcript = derived(
        transcriptsByCollection,
        ($transcripts) => $transcripts[collectionId] ?? []
    );
    // The transcript, then the complete messages of the turn that streams now.
    const messages = derived([transcript, liveTurn], ([$transcript, $liveTurn]) => [
        ...$transcript,
        ...$liveTurn.messages
    ]);
    const draft = derived(liveTurn, ($liveTurn) => $liveTurn.draft);

    const setTranscript = (value: AgentMessage[]) => {
        transcriptsByCollection.update((all) => ({ ...all, [collectionId]: value }));
    };

    /** Reads the events of one turn. Returns the GUI actions if the turn is complete. */
    const readTurn = async (response: Response): Promise<UiActions | null> => {
        for await (const event of readAgentStream(response.body!)) {
            if (event.type === 'turn_done') return event.ui_actions;
            if (event.type === 'turn_error') {
                error.set(event.detail);
                return null;
            }
            liveTurn.update((turn) => applyEvent(turn, event));
        }
        error.set('The agent stopped before it finished.');
        return null;
    };

    const send = async (text: string) => {
        const content = text.trim();
        if (!content || get(isSending)) return;
        const withQuestion = [...get(transcript), { role: 'user' as const, content }];
        setTranscript(withQuestion);
        isSending.set(true);
        error.set(null);
        let uiActions: UiActions | null = null;
        try {
            const response = await postTurn(collectionId, withQuestion, getSelectedSampleIds());
            if (response.ok && response.body) {
                uiActions = await readTurn(response);
            } else {
                error.set(await readErrorDetail(response));
            }
        } catch (err) {
            error.set(err instanceof Error ? err.message : String(err));
        } finally {
            setTranscript([...withQuestion, ...dropIncompleteStep(get(liveTurn).messages)]);
            liveTurn.set(EMPTY_LIVE_TURN);
            isSending.set(false);
        }
        if (uiActions) await onUiActions(uiActions);
    };

    const reset = () => {
        setTranscript([]);
        error.set(null);
    };

    return {
        messages,
        draft,
        isSending: readonly(isSending),
        error: readonly(error),
        send,
        reset
    };
}

function postTurn(
    collectionId: string,
    messages: AgentMessage[],
    selectedSampleIds: string[]
): Promise<Response> {
    return fetch(`${client.getConfig().baseUrl}/api/collections/${collectionId}/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages, selected_sample_ids: selectedSampleIds })
    });
}

async function readErrorDetail(response: Response): Promise<string> {
    try {
        const body: unknown = await response.json();
        const detail = (body as { detail?: unknown }).detail;
        if (typeof detail === 'string') return detail;
    } catch {
        // The body is not JSON. The generic message below describes the failure.
    }
    return 'The agent request failed.';
}
