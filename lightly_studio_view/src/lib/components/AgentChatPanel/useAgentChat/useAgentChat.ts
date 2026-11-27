import { client } from '$lib/api/lightly_studio_local/client.gen';
import type {
    AgentChatRequest,
    AgentMessage,
    TurnDoneEvent
} from '$lib/api/lightly_studio_local/types.gen';
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
    // The user picks a task after the greeting, until the first user message.
    const isPickingTask = derived(
        [transcript, isSending],
        ([$transcript, $isSending]) =>
            $transcript.length > 0 &&
            !$isSending &&
            $transcript.every((message) => message.role !== 'user')
    );

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

    /** Runs one turn and appends its messages to the transcript that the turn starts from. */
    const runTurn = async (startTranscript: AgentMessage[], request: () => Promise<Response>) => {
        setTranscript(startTranscript);
        isSending.set(true);
        error.set(null);
        let uiActions: UiActions | null = null;
        try {
            const response = await request();
            if (response.ok && response.body) {
                uiActions = await readTurn(response);
            } else {
                error.set(await readErrorDetail(response));
            }
        } catch (err) {
            error.set(err instanceof Error ? err.message : String(err));
        } finally {
            setTranscript([...startTranscript, ...dropIncompleteStep(get(liveTurn).messages)]);
            liveTurn.set(EMPTY_LIVE_TURN);
            isSending.set(false);
        }
        if (uiActions) await onUiActions(uiActions);
    };

    const send = async (text: string) => {
        const content = text.trim();
        if (!content || get(isSending)) return;
        const withQuestion = [...get(transcript), { role: 'user' as const, content }];
        await runTurn(withQuestion, () =>
            postAgent(collectionId, 'chat', {
                messages: withQuestion,
                selected_sample_ids: getSelectedSampleIds()
            })
        );
    };

    /** Starts a new conversation with the greeting of the agent. Does nothing in a conversation. */
    const greet = async () => {
        if (get(transcript).length > 0 || get(isSending)) return;
        await runTurn([], () => postAgent(collectionId, 'greeting'));
    };

    const reset = () => {
        setTranscript([]);
        error.set(null);
    };

    return {
        messages,
        draft,
        isSending: readonly(isSending),
        isPickingTask,
        error: readonly(error),
        send,
        greet,
        reset
    };
}

function postAgent(
    collectionId: string,
    endpoint: 'chat' | 'greeting',
    body?: AgentChatRequest
): Promise<Response> {
    const url = `${client.getConfig().baseUrl}/api/collections/${collectionId}/agent/${endpoint}`;
    if (!body) return fetch(url, { method: 'POST' });
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
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
