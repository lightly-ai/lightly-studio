import type { AgentMessageOutput } from '$lib/api/lightly_studio_local/types.gen';

type ChatEntry =
    | { kind: 'user' | 'assistant'; text: string }
    | { kind: 'tool'; name: string; summary: string; isError: boolean };

// The result keys of the agent tools that count samples, with the word that describes them.
const COUNT_KEYS: [string, string][] = [
    ['count', 'found'],
    ['tagged_count', 'tagged'],
    ['selected_count', 'selected'],
    ['shown_count', 'shown']
];

/**
 * Turns the agent transcript into the entries that the chat shows. A tool call and its
 * result become one entry with the tool name and a short summary.
 */
export function toChatEntries(messages: AgentMessageOutput[]): ChatEntry[] {
    const toolNames = new Map<string, string>();
    const entries: ChatEntry[] = [];
    for (const message of messages) {
        for (const call of message.tool_calls ?? []) {
            toolNames.set(call.id, call.function.name);
        }
        if (message.role === 'tool') {
            const name = toolNames.get(message.tool_call_id ?? '') ?? 'tool';
            entries.push({ kind: 'tool', name, ...summarizeToolResult(message.content ?? '') });
        } else if ((message.role === 'user' || message.role === 'assistant') && message.content) {
            entries.push({ kind: message.role, text: message.content });
        }
    }
    return entries;
}

function summarizeToolResult(content: string): { summary: string; isError: boolean } {
    let result: Record<string, unknown>;
    try {
        result = JSON.parse(content);
    } catch {
        return { summary: content, isError: false };
    }
    if (typeof result.error === 'string') {
        return { summary: result.error, isError: true };
    }
    const parts = COUNT_KEYS.filter(([key]) => typeof result[key] === 'number').map(
        ([key, word]) => `${result[key]} ${word}`
    );
    if (typeof result.tag_name === 'string') {
        parts.push(`tag "${result.tag_name}"`);
    }
    return { summary: parts.join(', ') || 'done', isError: false };
}
