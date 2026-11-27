import { afterEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useAgentChat } from './useAgentChat';

const ndjson = (events: object[]) =>
    new Response(events.map((event) => JSON.stringify(event) + '\n').join(''), { status: 200 });

const stubFetch = (response: Response) => {
    const fetchMock = vi.fn(async () => response);
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
};

describe('useAgentChat', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('sends the transcript and the selection, then applies the GUI actions', async () => {
        const uiActions = [{ type: 'select_tag' as const, tag_id: 't1', tag_name: 'tiger' }];
        const answer = { role: 'assistant', content: 'Tagged 2 images.', reasoning: 'Easy.' };
        const fetchMock = stubFetch(
            ndjson([
                { type: 'reasoning_delta', text: 'Easy.' },
                { type: 'message', message: answer },
                { type: 'turn_done', ui_actions: uiActions }
            ])
        );
        const onUiActions = vi.fn(async () => {});
        const chat = useAgentChat({
            collectionId: 'collection-1',
            getSelectedSampleIds: () => ['s1'],
            onUiActions
        });

        await chat.send('  Tag tigers  ');

        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toMatch(/\/api\/collections\/collection-1\/agent\/chat$/);
        expect(JSON.parse(init.body as string)).toEqual({
            messages: [{ role: 'user', content: 'Tag tigers' }],
            selected_sample_ids: ['s1']
        });
        expect(get(chat.messages)).toEqual([{ role: 'user', content: 'Tag tigers' }, answer]);
        expect(get(chat.draft)).toEqual({ reasoning: '', content: '' });
        expect(onUiActions).toHaveBeenCalledWith(uiActions);
        expect(get(chat.isSending)).toBe(false);
        expect(get(chat.isPickingTask)).toBe(false);
    });

    it('shows the error detail of a rejected request', async () => {
        stubFetch(
            new Response(JSON.stringify({ detail: 'The AI agent is off.' }), { status: 503 })
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

    it('keeps the complete steps of a turn that fails', async () => {
        const step = {
            role: 'assistant',
            tool_calls: [{ id: 'c1', type: 'function', function: { name: 'f', arguments: '{}' } }]
        };
        const result = { role: 'tool', tool_call_id: 'c1', content: '{}' };
        stubFetch(
            ndjson([
                { type: 'message', message: step },
                { type: 'message', message: result },
                { type: 'turn_error', detail: 'OpenRouter answered 429' }
            ])
        );
        const onUiActions = vi.fn();
        const chat = useAgentChat({
            collectionId: 'collection-3',
            getSelectedSampleIds: () => [],
            onUiActions
        });

        await chat.send('Go');

        expect(get(chat.error)).toBe('OpenRouter answered 429');
        expect(get(chat.messages)).toEqual([{ role: 'user', content: 'Go' }, step, result]);
        expect(onUiActions).not.toHaveBeenCalled();
    });

    it('reports a stream that ends before the turn is done', async () => {
        stubFetch(ndjson([{ type: 'content_delta', text: 'Hal' }]));
        const chat = useAgentChat({
            collectionId: 'collection-4',
            getSelectedSampleIds: () => [],
            onUiActions: vi.fn()
        });

        await chat.send('Hello');

        expect(get(chat.error)).toBe('The agent stopped before it finished.');
    });

    it('greet starts the conversation with the greeting of the agent', async () => {
        const greeting = { role: 'assistant', content: '- 3 images. What do you want to do?' };
        const fetchMock = stubFetch(
            ndjson([
                { type: 'message', message: greeting },
                { type: 'turn_done', ui_actions: [] }
            ])
        );
        const chat = useAgentChat({
            collectionId: 'collection-6',
            getSelectedSampleIds: () => [],
            onUiActions: vi.fn(async () => {})
        });

        await chat.greet();
        await chat.greet();

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url] = fetchMock.mock.calls[0] as unknown as [string];
        expect(url).toMatch(/\/api\/collections\/collection-6\/agent\/greeting$/);
        expect(get(chat.messages)).toEqual([greeting]);
        expect(get(chat.isPickingTask)).toBe(true);
    });

    it('reset clears the conversation', async () => {
        stubFetch(
            ndjson([
                { type: 'message', message: { role: 'assistant', content: 'Hi.' } },
                { type: 'turn_done', ui_actions: [] }
            ])
        );
        const chat = useAgentChat({
            collectionId: 'collection-5',
            getSelectedSampleIds: () => [],
            onUiActions: vi.fn(async () => {})
        });
        await chat.send('Hello');

        chat.reset();

        expect(get(chat.messages)).toEqual([]);
    });
});
