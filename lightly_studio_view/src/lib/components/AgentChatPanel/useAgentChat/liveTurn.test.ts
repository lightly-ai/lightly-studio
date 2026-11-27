import { describe, expect, it } from 'vitest';
import { dropIncompleteStep } from './liveTurn';

const toolCall = (id: string) => ({
    id,
    type: 'function' as const,
    function: { name: 'f', arguments: '{}' }
});

describe('dropIncompleteStep', () => {
    it('drops a last step that misses a tool result', () => {
        const user = { role: 'user' as const, content: 'Go' };
        const step = { role: 'assistant' as const, tool_calls: [toolCall('a'), toolCall('b')] };
        const result = { role: 'tool' as const, tool_call_id: 'a', content: '{}' };

        expect(dropIncompleteStep([user, step, result])).toEqual([user]);
    });

    it('keeps a transcript whose steps are complete', () => {
        const step = { role: 'assistant' as const, tool_calls: [toolCall('a')] };
        const result = { role: 'tool' as const, tool_call_id: 'a', content: '{}' };
        const answer = { role: 'assistant' as const, content: 'Done.' };

        expect(dropIncompleteStep([step, result, answer])).toEqual([step, result, answer]);
    });
});
