import { describe, expect, it } from 'vitest';
import { applyEvent, dropIncompleteStep, EMPTY_LIVE_TURN } from './liveTurn';

const toolCall = (id: string) => ({
    id,
    type: 'function' as const,
    function: { name: 'f', arguments: '{}' }
});

describe('applyEvent', () => {
    it('grows the draft, and a message replaces it', () => {
        let turn = applyEvent(EMPTY_LIVE_TURN, { type: 'reasoning_delta', text: 'Look ' });
        turn = applyEvent(turn, { type: 'reasoning_delta', text: 'first.' });
        turn = applyEvent(turn, { type: 'content_delta', text: 'I look.' });

        expect(turn.draft).toEqual({ reasoning: 'Look first.', content: 'I look.' });

        const message = { role: 'assistant' as const, content: 'I look.' };
        turn = applyEvent(turn, { type: 'message', message });

        expect(turn).toEqual({ messages: [message], draft: { reasoning: '', content: '' } });
    });
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
