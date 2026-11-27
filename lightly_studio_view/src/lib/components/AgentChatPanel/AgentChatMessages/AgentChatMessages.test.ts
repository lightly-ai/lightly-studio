import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { COLLECTION_OVERVIEW } from '../AgentChatSuggestions/suggestions';
import type { ChatTurn } from '../useAgentChat/chatHistory';
import AgentChatMessages from './AgentChatMessages.svelte';

const overviewMessages: ChatTurn['messages'] = [
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
        content: JSON.stringify({
            sample_count: 128,
            annotation_class_count: 69,
            annotation_classes: [
                { name: 'person', sample_count: 64 },
                { name: 'chair', sample_count: 27 },
                { name: 'dining table', sample_count: 15 },
                { name: 'apple', sample_count: 1 }
            ],
            tags: [],
            metadata: [],
            embedding_models: [{ name: 'mobileclip_s0', is_default: true }]
        })
    },
    {
        role: 'assistant',
        content: 'The collection overview is in; I’ll suggest ways to explore it.'
    }
];

const defaultProps = {
    liveText: '',
    liveReasoning: '',
    isSending: false,
    onPick: vi.fn(),
    onEdit: vi.fn()
};

describe('AgentChatMessages', () => {
    it('shows collection statistics and follow-ups even when the model only describes its next step', () => {
        render(AgentChatMessages, {
            props: {
                ...defaultProps,
                turns: [
                    {
                        prompt: COLLECTION_OVERVIEW.prompt,
                        status: 'done',
                        messages: overviewMessages
                    }
                ]
            }
        });

        const overview = within(screen.getByRole('region', { name: 'Collection overview' }));
        expect(overview.getByText('128')).toBeVisible();
        expect(overview.getByText('69')).toBeVisible();
        expect(overview.getByText('person')).toBeVisible();
        expect(overview.getByText('64 images')).toBeVisible();
        expect(overview.getByText('apple')).toBeVisible();
        expect(overview.getByText('mobileclip_s0')).toBeVisible();
        expect(screen.queryByText(/The collection overview is in/)).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'View person samples' })).toBeVisible();
    });

    it('keeps the written answer when the overview tool only supplied context for another task', () => {
        render(AgentChatMessages, {
            props: {
                ...defaultProps,
                turns: [
                    {
                        prompt: 'I want to select samples.',
                        status: 'done',
                        messages: [
                            ...overviewMessages.slice(0, 2),
                            {
                                role: 'assistant',
                                content: 'How many samples would you like to select?'
                            }
                        ]
                    }
                ]
            }
        });

        expect(screen.getByText('How many samples would you like to select?')).toBeVisible();
        expect(
            screen.queryByRole('region', { name: 'Collection overview' })
        ).not.toBeInTheDocument();
    });

    it('offers collection follow-ups after returning to the main view, even without model suggestions', async () => {
        const onPick = vi.fn();
        render(AgentChatMessages, {
            props: {
                turns: [
                    {
                        prompt: 'Return to the main view',
                        status: 'done',
                        messages: [
                            {
                                role: 'assistant',
                                tool_calls: [
                                    {
                                        id: 'show',
                                        type: 'function',
                                        function: {
                                            name: 'show_samples',
                                            arguments: '{"source":"all"}'
                                        }
                                    }
                                ]
                            },
                            { role: 'tool', tool_call_id: 'show', content: '{"shown_count":128}' },
                            {
                                role: 'assistant',
                                content: 'Back in the main view, showing all 128 images.'
                            }
                        ]
                    }
                ],
                ...defaultProps,
                onPick
            }
        });

        expect(screen.getByText('Back in the main view, showing all 128 images.')).toBeVisible();
        expect(screen.getByRole('button', { name: 'Summarize this collection' })).toBeVisible();
        await fireEvent.click(screen.getByRole('button', { name: 'See class distribution' }));

        expect(onPick).toHaveBeenCalledExactlyOnceWith(
            'Show how many samples have each annotation class in the full collection.'
        );
    });
});
