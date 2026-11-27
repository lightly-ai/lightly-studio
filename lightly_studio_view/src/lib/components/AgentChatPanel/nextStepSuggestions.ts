import type { AgentMessage } from '$lib/api/lightly_studio_local/types.gen';
import type { Suggestion } from './AgentChatSuggestions/suggestions';

/** The name of the agent tool that suggests the next steps. Its call ends the turn. */
export const SUGGEST_NEXT_STEPS = 'suggest_next_steps';

/**
 * Gets the next steps that the agent suggested at the end of the last turn. The suggestion
 * ends the turn, so only a transcript that ends with its tool result has current steps.
 */
export function getNextStepSuggestions(messages: AgentMessage[]): Suggestion[] {
    if (messages.at(-1)?.role !== 'tool') return [];
    const lastStep = messages.findLast((message) => message.role === 'assistant');
    const call = lastStep?.tool_calls?.find(
        (toolCall) => toolCall.function.name === SUGGEST_NEXT_STEPS
    );
    return call ? parseSteps(call.function.arguments) : [];
}

function parseSteps(argumentsJson: string): Suggestion[] {
    let parsed: unknown;
    try {
        parsed = JSON.parse(argumentsJson);
    } catch {
        return [];
    }
    const steps = (parsed as { steps?: unknown } | null)?.steps;
    return Array.isArray(steps) ? steps.filter(isSuggestion) : [];
}

function isSuggestion(value: unknown): value is Suggestion {
    const candidate = value as Partial<Suggestion> | null;
    return typeof candidate?.label === 'string' && typeof candidate.prompt === 'string';
}
