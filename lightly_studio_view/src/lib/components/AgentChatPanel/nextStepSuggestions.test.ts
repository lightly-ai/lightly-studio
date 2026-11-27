import { describe, expect, it } from 'vitest';
import type { AgentMessage } from '$lib/api/lightly_studio_local/types.gen';
import { getNextStepSuggestions } from './nextStepSuggestions';

const steps = [
    { label: 'Tag these samples', prompt: 'Tag the 12 samples as clock.' },
    { label: 'Find similar', prompt: 'Find 20 samples similar to these.' }
];

const answerWithSuggestion = (argumentsJson: string): AgentMessage[] => [
    { role: 'user', content: 'Find clocks' },
    {
        role: 'assistant',
        content: 'I found 12 clock images.',
        tool_calls: [
            {
                id: 'call_1',
                type: 'function',
                function: { name: 'suggest_next_steps', arguments: argumentsJson }
            }
        ]
    },
    { role: 'tool', tool_call_id: 'call_1', content: '{"suggested_count": 2}' }
];

describe('getNextStepSuggestions', () => {
    it('gets the steps of the suggestion that ends the transcript', () => {
        const messages = answerWithSuggestion(JSON.stringify({ steps }));

        expect(getNextStepSuggestions(messages)).toEqual(steps);
    });

    it('gets no steps when the last turn has no suggestion', () => {
        const messages: AgentMessage[] = [
            { role: 'user', content: 'Hello' },
            { role: 'assistant', content: 'Hello. What do you want to do?' }
        ];

        expect(getNextStepSuggestions(messages)).toEqual([]);
    });

    it('gets no steps after a new user message', () => {
        const messages = [
            ...answerWithSuggestion(JSON.stringify({ steps })),
            { role: 'user' as const, content: 'Tag the 12 samples as clock.' }
        ];

        expect(getNextStepSuggestions(messages)).toEqual([]);
    });

    it('drops arguments that are not valid steps', () => {
        expect(getNextStepSuggestions(answerWithSuggestion('{"steps": ['))).toEqual([]);
        const mixed = JSON.stringify({ steps: [steps[0], { label: 'No prompt' }] });
        expect(getNextStepSuggestions(answerWithSuggestion(mixed))).toEqual([steps[0]]);
    });
});
