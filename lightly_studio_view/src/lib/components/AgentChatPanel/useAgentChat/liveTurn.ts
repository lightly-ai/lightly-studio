import type { AgentMessage, AgentStreamLine } from '$lib/api/lightly_studio_local/types.gen';

/** The part of an agent turn that has arrived so far. */
interface LiveTurn {
    /** The complete messages of the turn, in order. */
    messages: AgentMessage[];
    /** The text of the step that the model writes now. A new message replaces it. */
    draft: { reasoning: string; content: string };
}

export const EMPTY_LIVE_TURN: LiveTurn = { messages: [], draft: { reasoning: '', content: '' } };

/** Adds one stream event to the live turn. The end events of a turn change nothing. */
export function applyEvent(turn: LiveTurn, event: AgentStreamLine): LiveTurn {
    switch (event.type) {
        case 'reasoning_delta':
            return {
                ...turn,
                draft: { ...turn.draft, reasoning: turn.draft.reasoning + event.text }
            };
        case 'content_delta':
            return { ...turn, draft: { ...turn.draft, content: turn.draft.content + event.text } };
        case 'message':
            return { messages: [...turn.messages, event.message], draft: EMPTY_LIVE_TURN.draft };
        default:
            return turn;
    }
}

/**
 * Drops a last step whose tool calls do not all have a result. The model rejects a
 * transcript with such a step, so a broken stream must not leave one behind.
 */
export function dropIncompleteStep(messages: AgentMessage[]): AgentMessage[] {
    const stepIndex = messages.findLastIndex((message) => message.tool_calls?.length);
    if (stepIndex === -1) return messages;
    const callCount = messages[stepIndex].tool_calls?.length ?? 0;
    const resultCount = messages.length - stepIndex - 1;
    return resultCount < callCount ? messages.slice(0, stepIndex) : messages;
}
