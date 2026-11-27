import type { AgentMessage } from '$lib/api/lightly_studio_local/types.gen';

type ToolStatus = 'running' | 'done' | 'error';

type ChatEntry =
    | { kind: 'user' | 'assistant' | 'step' | 'thinking'; text: string }
    | { kind: 'tool'; callId: string; name: string; status: ToolStatus; summary: string };

// The result keys of the agent tools that count samples, with the word that describes them.
const COUNT_KEYS: [string, string][] = [
    ['count', 'found'],
    ['tagged_count', 'tagged'],
    ['selected_count', 'selected'],
    ['shown_count', 'shown']
];

/**
 * Turns the agent transcript into the entries that the chat shows. The reasoning of a step
 * becomes a thinking entry, and its text a step entry. A tool call becomes a running tool
 * entry, which its result completes.
 */
export function toChatEntries(messages: AgentMessage[]): ChatEntry[] {
    const entries: ChatEntry[] = [];
    const toolEntries = new Map<string, Extract<ChatEntry, { kind: 'tool' }>>();
    for (const message of messages) {
        if (message.role === 'user' && message.content) {
            entries.push({ kind: 'user', text: message.content });
        } else if (message.role === 'assistant') {
            entries.push(...assistantEntries(message, toolEntries));
        } else if (message.role === 'tool') {
            const entry = toolEntries.get(message.tool_call_id ?? '');
            if (entry) Object.assign(entry, summarizeToolResult(message.content ?? ''));
        }
    }
    return entries;
}

function assistantEntries(
    message: AgentMessage,
    toolEntries: Map<string, Extract<ChatEntry, { kind: 'tool' }>>
): ChatEntry[] {
    const calls = message.tool_calls ?? [];
    const entries: ChatEntry[] = [];
    if (message.reasoning) entries.push({ kind: 'thinking', text: message.reasoning });
    if (message.content) {
        entries.push({ kind: calls.length ? 'step' : 'assistant', text: message.content });
    }
    for (const call of calls) {
        const entry = {
            kind: 'tool' as const,
            callId: call.id,
            name: call.function.name,
            status: 'running' as ToolStatus,
            summary: 'running…'
        };
        toolEntries.set(call.id, entry);
        entries.push(entry);
    }
    return entries;
}

function summarizeToolResult(content: string): { status: ToolStatus; summary: string } {
    let result: Record<string, unknown>;
    try {
        result = JSON.parse(content);
    } catch {
        return { status: 'done', summary: content };
    }
    if (typeof result.error === 'string') {
        return { status: 'error', summary: result.error };
    }
    // An operator reports its own success and message.
    if (typeof result.success === 'boolean') {
        return { status: result.success ? 'done' : 'error', summary: String(result.message) };
    }
    const parts = COUNT_KEYS.filter(([key]) => typeof result[key] === 'number').map(
        ([key, word]) => `${result[key]} ${word}`
    );
    if (typeof result.tag_name === 'string') {
        parts.push(`tag "${result.tag_name}"`);
    }
    if (Array.isArray(result.strategies)) {
        parts.push(result.strategies.join(' + '));
    }
    if (typeof result.computed === 'string') {
        parts.push(`${result.computed} stored as "${result.metadata_name}"`);
    }
    return { status: 'done', summary: parts.join(', ') || 'done' };
}
