import { describe, expect, it } from 'vitest';
import { toChatEntries } from './toChatEntries';

const toolCall = (id: string, name: string) => ({
    role: 'assistant' as const,
    tool_calls: [{ id, type: 'function' as const, function: { name, arguments: '{}' } }]
});

describe('toChatEntries', () => {
    it('shows user and assistant text and one entry per tool result', () => {
        const entries = toChatEntries([
            { role: 'user', content: 'Find tigers' },
            toolCall('call_1', 'search_by_text'),
            {
                role: 'tool',
                tool_call_id: 'call_1',
                content: JSON.stringify({ result: 'result_1', count: 10, best_matches: [] })
            },
            toolCall('call_2', 'tag_samples'),
            {
                role: 'tool',
                tool_call_id: 'call_2',
                content: JSON.stringify({ tag_name: 'tiger', tagged_count: 10 })
            },
            { role: 'assistant', content: 'Tagged 10 images.' }
        ]);

        expect(entries).toEqual([
            { kind: 'user', text: 'Find tigers' },
            { kind: 'tool', name: 'search_by_text', summary: '10 found', isError: false },
            {
                kind: 'tool',
                name: 'tag_samples',
                summary: '10 tagged, tag "tiger"',
                isError: false
            },
            { kind: 'assistant', text: 'Tagged 10 images.' }
        ]);
    });

    it('marks a tool error', () => {
        const entries = toChatEntries([
            toolCall('call_1', 'show_samples'),
            {
                role: 'tool',
                tool_call_id: 'call_1',
                content: JSON.stringify({ error: 'Unknown result handle' })
            }
        ]);

        expect(entries).toEqual([
            { kind: 'tool', name: 'show_samples', summary: 'Unknown result handle', isError: true }
        ]);
    });
});
