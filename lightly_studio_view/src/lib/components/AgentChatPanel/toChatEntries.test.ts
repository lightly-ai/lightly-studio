import { describe, expect, it } from 'vitest';
import { toChatEntries } from './toChatEntries';

const toolCall = (id: string, name: string) => ({
    role: 'assistant' as const,
    tool_calls: [{ id, type: 'function' as const, function: { name, arguments: '{}' } }]
});

describe('toChatEntries', () => {
    it('shows user and assistant text and one entry per tool call', () => {
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
            {
                kind: 'tool',
                callId: 'call_1',
                name: 'search_by_text',
                status: 'done',
                summary: '10 found'
            },
            {
                kind: 'tool',
                callId: 'call_2',
                name: 'tag_samples',
                status: 'done',
                summary: '10 tagged, tag "tiger"'
            },
            { kind: 'assistant', text: 'Tagged 10 images.' }
        ]);
    });

    it('shows the reasoning and the text of a step, and a tool without result as running', () => {
        const entries = toChatEntries([
            {
                ...toolCall('call_1', 'get_collection_overview'),
                reasoning: 'I need the size first.',
                content: 'I check the collection.'
            }
        ]);

        expect(entries).toEqual([
            { kind: 'thinking', text: 'I need the size first.' },
            { kind: 'step', text: 'I check the collection.' },
            {
                kind: 'tool',
                callId: 'call_1',
                name: 'get_collection_overview',
                status: 'running',
                summary: 'running…'
            }
        ]);
    });

    it('summarizes a combined selection and a metadata computation', () => {
        const entries = toChatEntries([
            {
                role: 'assistant',
                tool_calls: [
                    {
                        id: 'c1',
                        type: 'function',
                        function: { name: 'compute_metadata', arguments: '{}' }
                    },
                    {
                        id: 'c2',
                        type: 'function',
                        function: { name: 'run_selection', arguments: '{}' }
                    }
                ]
            },
            {
                role: 'tool',
                tool_call_id: 'c1',
                content: JSON.stringify({ metadata_name: 'typicality', computed: 'typicality' })
            },
            {
                role: 'tool',
                tool_call_id: 'c2',
                content: JSON.stringify({
                    tag_name: 'picked',
                    selected_count: 200,
                    result: 'result_2',
                    strategies: ['diversity x2', 'weights(typicality) x1']
                })
            }
        ]);

        expect(entries.map((entry) => entry.kind === 'tool' && entry.summary)).toEqual([
            'typicality stored as "typicality"',
            '200 selected, tag "picked", diversity x2 + weights(typicality) x1'
        ]);
    });

    it('shows the message of an operator, and its failure as an error', () => {
        const entries = toChatEntries([
            toolCall('call_1', 'run_operator'),
            {
                role: 'tool',
                tool_call_id: 'call_1',
                content: JSON.stringify({ operator: 'sam', success: false, message: 'No GPU.' })
            }
        ]);

        expect(entries).toEqual([
            {
                kind: 'tool',
                callId: 'call_1',
                name: 'run_operator',
                status: 'error',
                summary: 'No GPU.'
            }
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
            {
                kind: 'tool',
                callId: 'call_1',
                name: 'show_samples',
                status: 'error',
                summary: 'Unknown result handle'
            }
        ]);
    });

    it('shows an answer with suggested next steps as an answer, without a tool entry', () => {
        const entries = toChatEntries([
            { role: 'user', content: 'Find clocks' },
            { ...toolCall('call_1', 'suggest_next_steps'), content: 'I found 12 clock images.' },
            { role: 'tool', tool_call_id: 'call_1', content: '{"suggested_count": 2}' }
        ]);

        expect(entries).toEqual([
            { kind: 'user', text: 'Find clocks' },
            { kind: 'assistant', text: 'I found 12 clock images.' }
        ]);
    });
});
