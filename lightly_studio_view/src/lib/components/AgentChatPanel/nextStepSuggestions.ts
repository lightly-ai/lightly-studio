import type { AgentMessage } from '$lib/api/lightly_studio_local';
import type { Suggestion } from './AgentChatSuggestions/suggestions';
import { completedToolCalls, parseObject } from './completedToolCalls';
import { suggestFromToolResult } from './suggestFromToolResult';

export const SUGGEST_NEXT_STEPS = 'suggest_next_steps';
const MAX_SUGGESTIONS = 3;

/** Gets follow-ups from the current turn, with a fallback based on completed tools. */
export function getNextStepSuggestions(messages: AgentMessage[]): Suggestion[] {
    const turnStart = messages.findLastIndex((message) => message.role === 'user') + 1;
    const turn = messages.slice(turnStart);
    const calls = completedToolCalls(turn);
    for (const { call } of calls) {
        if (call.function.name !== SUGGEST_NEXT_STEPS) continue;
        const steps = parseSteps(call.function.arguments);
        if (steps.length) return steps;
    }

    const answer = turn.findLast((message) => message.role === 'assistant');
    const answerText = answer?.content?.trim();
    if (!answerText) return [];
    if (answer?.tool_calls?.some((call) => call.function.name !== SUGGEST_NEXT_STEPS)) return [];
    // Only the model knows the options of its own question. A guessed step would contradict it.
    if (answerText.endsWith('?')) return [];
    const latestWork = calls.find(({ call }) => call.function.name !== SUGGEST_NEXT_STEPS);
    return latestWork
        ? suggestFromToolResult(latestWork.call.function.name, latestWork.result)
        : [];
}

function parseSteps(argumentsJson: string): Suggestion[] {
    const steps = parseObject(argumentsJson)?.steps;
    return Array.isArray(steps) ? steps.filter(isSuggestion).slice(0, MAX_SUGGESTIONS) : [];
}

function isSuggestion(value: unknown): value is Suggestion {
    const candidate = value as Partial<Suggestion> | null;
    return (
        typeof candidate?.label === 'string' &&
        Boolean(candidate.label.trim()) &&
        typeof candidate.prompt === 'string' &&
        Boolean(candidate.prompt.trim())
    );
}
