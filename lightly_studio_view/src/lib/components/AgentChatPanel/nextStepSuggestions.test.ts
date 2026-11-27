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

    it('keeps suggestions when a separate written answer follows a suggestion-only step', () => {
        const [question, suggestion, result] = answerWithSuggestion(JSON.stringify({ steps }));
        const messages: AgentMessage[] = [
            question,
            { ...suggestion, content: null },
            result,
            { role: 'assistant', content: 'I found 12 clock images.' }
        ];

        expect(getNextStepSuggestions(messages)).toEqual(steps);
    });

    it('keeps suggestions issued in the same batch as a collection tool', () => {
        const [question, suggestion, result] = answerWithSuggestion(JSON.stringify({ steps }));
        const messages: AgentMessage[] = [
            question,
            {
                ...suggestion,
                content: null,
                tool_calls: [
                    ...(suggestion.tool_calls ?? []),
                    {
                        id: 'overview',
                        type: 'function',
                        function: { name: 'get_collection_overview', arguments: '{}' }
                    }
                ]
            },
            result,
            { role: 'tool', tool_call_id: 'overview', content: '{"sample_count":128}' },
            { role: 'assistant', content: 'I found 12 clock images.' }
        ];

        expect(getNextStepSuggestions(messages)).toEqual(steps);
    });

    it('uses actual annotation classes when the overview has no model suggestions', () => {
        const messages: AgentMessage[] = [
            {
                role: 'assistant',
                tool_calls: [
                    {
                        id: 'overview',
                        type: 'function',
                        function: { name: 'get_collection_overview', arguments: '{}' }
                    }
                ]
            },
            {
                role: 'tool',
                tool_call_id: 'overview',
                content:
                    '{"sample_count":128,"annotation_classes":[{"name":"person","sample_count":64}],"embedding_models":[]}'
            },
            { role: 'assistant', content: 'This collection has 128 images.' }
        ];

        expect(getNextStepSuggestions(messages).map(({ label }) => label)).toEqual([
            'View person samples',
            'See class distribution'
        ]);
    });

    it('gets no fallback steps when the answer is a question', () => {
        const messages: AgentMessage[] = [
            {
                role: 'assistant',
                tool_calls: [
                    {
                        id: 'classes',
                        type: 'function',
                        function: { name: 'list_annotation_classes', arguments: '{}' }
                    }
                ]
            },
            {
                role: 'tool',
                tool_call_id: 'classes',
                content: '{"annotation_classes":[{"name":"person","sample_count":64}]}'
            },
            {
                role: 'assistant',
                content: 'There are 5 samples annotated with dogs. Use them, or search by text?'
            }
        ];

        expect(getNextStepSuggestions(messages)).toEqual([]);
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
