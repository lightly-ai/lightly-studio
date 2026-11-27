import type { AgentMessage } from '$lib/api/lightly_studio_local';

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
