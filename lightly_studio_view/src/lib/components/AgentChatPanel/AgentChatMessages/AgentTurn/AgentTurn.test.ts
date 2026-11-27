import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import AgentTurn from './AgentTurn.svelte';

const defaultProps = {
    turn: { prompt: 'Find tigers', messages: [], status: 'done' as const },
    liveText: '',
    liveReasoning: '',
    suggestions: [],
    suggestionsDisabled: false,
    onPick: vi.fn(),
    onEdit: vi.fn()
};

describe('AgentTurn', () => {
    it('explains a saved turn without answer text and keeps its follow-up buttons available', () => {
        render(AgentTurn, {
            props: {
                ...defaultProps,
                turn: {
                    prompt: 'Give me the dataset statistics',
                    messages: [
                        { role: 'assistant', content: '  ', reasoning: 'Internal reasoning' }
                    ],
                    status: 'done'
                },
                suggestions: [{ label: 'View person samples', prompt: 'View person samples' }]
            }
        });

        expect(screen.getByText(/finished without a written answer/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Edit message' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'View person samples' })).toBeEnabled();
        // The thoughts wait in the closed activity log.
        expect(screen.getByText('Internal reasoning')).not.toBeVisible();
    });

    it('offers a retry of a failed turn as an alert', async () => {
        const onPick = vi.fn();
        render(AgentTurn, {
            props: {
                ...defaultProps,
                turn: { prompt: 'Find tigers', messages: [], status: 'failed', error: 'No key.' },
                onPick
            }
        });

        expect(screen.getByRole('alert')).toHaveTextContent('No key.');
        await fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
        expect(onPick).toHaveBeenCalledExactlyOnceWith('Find tigers');
    });

    it('shows the live thinking with its heading and the elapsed time', () => {
        vi.useFakeTimers({ now: 20_000 });
        render(AgentTurn, {
            props: {
                ...defaultProps,
                turn: { prompt: 'Find tigers', messages: [], status: 'running', startedAt: 13_000 },
                liveReasoning: '**Planning the selection**\n\nThe user wants tigers.'
            }
        });

        expect(screen.getByTestId('agent-activity-progress')).toHaveTextContent(
            'Thinking · Planning the selection'
        );
        expect(screen.getByTestId('agent-thinking-preview')).toHaveTextContent(
            'The user wants tigers.'
        );
        expect(screen.getByLabelText('Elapsed time')).toHaveTextContent('7s');
        vi.useRealTimers();
    });

    it('keeps the thoughts of a finished turn in the activity log with its duration', () => {
        render(AgentTurn, {
            props: {
                ...defaultProps,
                turn: {
                    prompt: 'How many images?',
                    status: 'done',
                    startedAt: 1_000,
                    finishedAt: 10_000,
                    messages: [
                        {
                            role: 'assistant',
                            reasoning: '**Counting**\n\nThe overview has the count.',
                            content: 'The collection has 128 images.'
                        }
                    ]
                }
            }
        });

        expect(screen.getByText(/Worked for 9s/)).toBeInTheDocument();
        expect(screen.getByText('Thought')).toBeInTheDocument();
        expect(screen.getByText(/The overview has the count\./)).toBeInTheDocument();
        expect(screen.queryByTestId('agent-progress')).not.toBeInTheDocument();
    });

    it('shows the latest step of the agent while it works', () => {
        render(AgentTurn, {
            props: {
                ...defaultProps,
                turn: {
                    prompt: 'Find tigers',
                    status: 'running',
                    messages: [
                        {
                            role: 'assistant',
                            content: 'I check the annotation classes first.',
                            tool_calls: [
                                {
                                    id: 'c1',
                                    type: 'function',
                                    function: { name: 'list_annotation_classes', arguments: '{}' }
                                }
                            ]
                        },
                        { role: 'tool', tool_call_id: 'c1', content: '{"annotation_classes":[]}' }
                    ]
                }
            }
        });

        expect(screen.getByTestId('agent-activity-progress')).toHaveTextContent(
            'I check the annotation classes first.'
        );
    });
});
