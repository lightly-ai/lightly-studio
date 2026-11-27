import type { AgentMessage } from '$lib/api/lightly_studio_local';

type ToolCall = NonNullable<AgentMessage['tool_calls']>[number];

interface CompletedCall {
    call: ToolCall;
    result: Record<string, unknown>;
}

export function completedToolCalls(messages: AgentMessage[]): CompletedCall[] {
    const calls = new Map(
        messages.flatMap((message) => message.tool_calls ?? []).map((call) => [call.id, call])
    );
    return messages.toReversed().flatMap((message) => {
        if (message.role !== 'tool' || !message.tool_call_id) return [];
        const call = calls.get(message.tool_call_id);
        const result = parseObject(message.content ?? '');
        if (!call || !result || result.error || result.success === false) return [];
        return [{ call, result }];
    });
}

export function parseObject(json: string): Record<string, unknown> | undefined {
    try {
        const value: unknown = JSON.parse(json);
        if (value && typeof value === 'object' && !Array.isArray(value)) {
            return value as Record<string, unknown>;
        }
    } catch {
        return undefined;
    }
    return undefined;
}
