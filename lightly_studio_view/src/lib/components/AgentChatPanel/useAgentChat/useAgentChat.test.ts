import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { agentChat } from '$lib/api/lightly_studio_local/sdk.gen';
import { useAgentChat } from './useAgentChat';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({ agentChat: vi.fn() }));

const mockedAgentChat = vi.mocked(agentChat);

// The tests need only the `data` and `error` fields of the SDK response.
const asResponse = (value: unknown) => value as Awaited<ReturnType<typeof agentChat>>;

describe('useAgentChat', () => {
    beforeEach(() => {
        mockedAgentChat.mockReset();
    });

    it('sends the transcript and the selection, then applies the GUI actions', async () => {
        const uiActions = [{ type: 'select_tag' as const, tag_id: 't1', tag_name: 'tiger' }];
        mockedAgentChat.mockResolvedValue(
            asResponse({
                data: {
                    messages: [{ role: 'assistant', content: 'Tagged 2 images.' }],
                    ui_actions: uiActions
                }
            })
        );
        const onUiActions = vi.fn(async () => {});
        const chat = useAgentChat({
            collectionId: 'collection-1',
            getSelectedSampleIds: () => ['s1'],
            onUiActions
        });

        await chat.send('  Tag tigers  ');

        expect(mockedAgentChat).toHaveBeenCalledWith({
            path: { collection_id: 'collection-1' },
            body: {
                messages: [{ role: 'user', content: 'Tag tigers' }],
                selected_sample_ids: ['s1']
            }
        });
        expect(get(chat.messages)).toEqual([
            { role: 'user', content: 'Tag tigers' },
            { role: 'assistant', content: 'Tagged 2 images.' }
        ]);
        expect(onUiActions).toHaveBeenCalledWith(uiActions);
        expect(get(chat.isSending)).toBe(false);
    });

    it('shows the error detail of a failed request', async () => {
        mockedAgentChat.mockResolvedValue(
            asResponse({
                data: undefined,
                error: { detail: 'The AI agent is off.' }
            })
        );
        const chat = useAgentChat({
            collectionId: 'collection-2',
            getSelectedSampleIds: () => [],
            onUiActions: vi.fn()
        });

        await chat.send('Hello');

        expect(get(chat.error)).toBe('The AI agent is off.');
        expect(get(chat.messages)).toEqual([{ role: 'user', content: 'Hello' }]);
    });

    it('reset clears the conversation', async () => {
        mockedAgentChat.mockResolvedValue(
            asResponse({
                data: { messages: [{ role: 'assistant', content: 'Hi.' }], ui_actions: [] }
            })
        );
        const chat = useAgentChat({
            collectionId: 'collection-3',
            getSelectedSampleIds: () => [],
            onUiActions: vi.fn(async () => {})
        });
        await chat.send('Hello');

        chat.reset();

        expect(get(chat.messages)).toEqual([]);
    });
});
