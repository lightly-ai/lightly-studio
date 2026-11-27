import { client } from '$lib/api/lightly_studio_local/client.gen';
import type {
    AgentChatRequest,
    AgentMessage,
    AgentStreamLine,
    TurnDoneEvent
} from '$lib/api/lightly_studio_local';
import { derived, get, writable } from 'svelte/store';
import { v4 as uuid } from 'uuid';
import {
    chatHistory,
    createChatHistory,
    INTERRUPTED,
    NEW_CHAT,
    STOPPED,
    type ChatHistory,
    type ChatTurn,
    type Conversation
} from './chatHistory';
import { dropIncompleteStep } from './liveTurn';
import { readAgentStream } from './readAgentStream';

type UiActions = TurnDoneEvent['ui_actions'];

/** The text of the step that the model writes now. The next message replaces it. */
interface LiveReply {
    id: string;
    text: string;
    reasoning: string;
}

interface ChatOptions {
    collectionId: string;
    getSelectedSampleIds: () => string[];
    onUiActions: (actions: UiActions) => Promise<void>;
}

const sessions = new Map<string, ReturnType<typeof createAgentChat>>();

export function useAgentChat({ collectionId, getSelectedSampleIds, onUiActions }: ChatOptions) {
    const session = sessions.get(collectionId) ?? createAgentChat(collectionId);
    sessions.set(collectionId, session);

    return {
        ...session,
        send: (text: string) => session.send(text, getSelectedSampleIds, onUiActions)
    };
}

export function createAgentChat(collectionId: string, storage: ChatHistory = chatHistory) {
    const { conversations, activeId, storageError, ready, select, update } = createChatHistory(
        collectionId,
        storage
    );
    const isLoading = writable(true);
    const isSending = writable(false);
    const liveReply = writable<LiveReply | null>(null);
    let turnAbort: AbortController | undefined;
    const active = derived([conversations, activeId], ([$all, $id]) => $all[$id]);
    const history = derived(conversations, ($all) =>
        Object.values($all)
            .filter((conversation) => conversation.turns.length)
            .sort((a, b) => b.updatedAt - a.updatedAt)
    );

    void ready.then(() => isLoading.set(false));

    function setDraft(draft: string) {
        const conversation = get(active) ?? newConversation(NEW_CHAT);
        update({ ...conversation, draft });
    }

    function newChat() {
        select(NEW_CHAT);
    }

    function stop() {
        turnAbort?.abort();
    }

    async function send(
        text: string,
        getSelectedSampleIds: () => string[],
        onUiActions: (actions: UiActions) => Promise<void>
    ) {
        const prompt = text.trim();
        if (!prompt || get(isSending) || get(isLoading)) return;

        const current = get(active);
        const starting = !current || current.id === NEW_CHAT;
        const conversation = starting ? newConversation(uuid()) : current;
        const { id, turns } = conversation;
        const draft = current?.draft.trim() === prompt ? '' : (current?.draft ?? '');
        const messages = [
            ...turns.flatMap(toRequestMessages),
            { role: 'user' as const, content: prompt }
        ];
        let turn: ChatTurn = { prompt, messages: [], status: 'running', startedAt: Date.now() };

        function saveTurn() {
            const saved = get(conversations)[id] ?? { ...conversation, draft };
            update({ ...saved, updatedAt: Date.now(), turns: [...turns, turn] });
        }

        const abort = new AbortController();
        turnAbort = abort;
        isSending.set(true);
        update({ ...conversation, draft, updatedAt: Date.now(), turns: [...turns, turn] });
        if (starting) {
            if (current?.draft) update({ ...current, draft: '' });
            select(id);
        }
        try {
            const actions = await streamTurn(
                collectionId,
                {
                    messages,
                    selected_sample_ids: getSelectedSampleIds()
                },
                (event) => {
                    if (event.type === 'content_delta') {
                        liveReply.update((reply) => ({
                            id,
                            text: (reply?.text ?? '') + event.text,
                            reasoning: reply?.reasoning ?? ''
                        }));
                    } else if (event.type === 'reasoning_delta') {
                        liveReply.update((reply) => ({
                            id,
                            text: reply?.text ?? '',
                            reasoning: (reply?.reasoning ?? '') + event.text
                        }));
                    } else if (event.type === 'message') {
                        turn = { ...turn, messages: [...turn.messages, event.message] };
                        saveTurn();
                        liveReply.set(null);
                    }
                },
                abort.signal
            );
            turn = { ...turn, status: 'done', finishedAt: Date.now() };
            saveTurn();
            try {
                await onUiActions(actions);
            } catch {
                turn = { ...turn, error: 'The reply finished, but the grid could not be updated.' };
                saveTurn();
            }
        } catch (error) {
            turn = {
                ...turn,
                status: 'failed',
                finishedAt: Date.now(),
                error: describeFailure(error, abort.signal)
            };
            saveTurn();
        } finally {
            turnAbort = undefined;
            liveReply.set(null);
            isSending.set(false);
        }
    }

    return {
        active,
        activeId,
        history,
        isLoading,
        isSending,
        liveReply,
        storageError,
        ready,
        newChat,
        select,
        setDraft,
        send,
        stop
    };
}

function newConversation(id: string): Conversation {
    return { id, updatedAt: Date.now(), draft: '', turns: [] };
}

/**
 * Gets the messages of an earlier turn for the next request. A turn that failed before the
 * agent answered is left out, because two user messages in a row confuse the model.
 */
function toRequestMessages(turn: ChatTurn): AgentMessage[] {
    const answered = dropIncompleteStep(turn.messages);
    return answered.length ? [{ role: 'user', content: turn.prompt }, ...answered] : [];
}

function describeFailure(error: unknown, signal: AbortSignal): string {
    if (signal.aborted) return STOPPED;
    return error instanceof Error ? error.message : INTERRUPTED;
}

async function streamTurn(
    collectionId: string,
    body: AgentChatRequest,
    onEvent: (event: AgentStreamLine) => void,
    signal: AbortSignal
): Promise<UiActions> {
    const url = `${client.getConfig().baseUrl}/api/collections/${collectionId}/agent/chat`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal
    });
    if (!response.ok || !response.body) throw new Error(await readErrorDetail(response));
    for await (const event of readAgentStream(response.body)) {
        if (event.type === 'turn_done') return event.ui_actions;
        if (event.type === 'turn_error') throw new Error(event.detail);
        onEvent(event);
    }
    throw new Error(INTERRUPTED);
}

async function readErrorDetail(response: Response): Promise<string> {
    const body: { detail?: unknown; error?: unknown } | null = await response
        .json()
        .catch(() => null);
    const detail = body?.detail ?? body?.error;
    return typeof detail === 'string'
        ? detail
        : 'The agent could not answer. Try sending your message again.';
}
