import { afterEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { STOPPED, type ChatHistory } from './chatHistory';
import { createAgentChat } from './useAgentChat';

function memoryHistory(): ChatHistory {
    const saved = new Map<string, Awaited<ReturnType<ChatHistory['load']>>[number]>();
    return {
        load: async (collectionId) =>
            [...saved.values()].filter((record) => record.collectionId === collectionId),
        save: async (record) => {
            saved.set(JSON.stringify([record.collectionId, record.id]), record);
        }
    };
}

const ndjson = (events: object[]) =>
    new Response(events.map((event) => JSON.stringify(event) + '\n').join(''));

const answer = { role: 'assistant', content: 'Tagged 2 samples.' };
const done = {
    type: 'turn_done',
    ui_actions: [{ type: 'select_tag', tag_id: 't1', tag_name: 'tiger' }]
};
const doneReply = () => ndjson([{ type: 'message', message: answer }, done]);
const selection = () => ['s1'];
const noop = async () => {};

describe('chat conversations', () => {
    afterEach(() => vi.unstubAllGlobals());

    it('opens without a greeting and sends the live selection before applying grid actions', async () => {
        const fetchMock = vi.fn<typeof fetch>(async () => doneReply());
        vi.stubGlobal('fetch', fetchMock);
        const chat = createAgentChat('images', memoryHistory());
        await chat.ready;
        expect(fetchMock).not.toHaveBeenCalled();

        chat.setDraft('  Tag tigers  ');
        const onUiActions = vi.fn(async () => {});
        await chat.send('  Tag tigers  ', selection, onUiActions);

        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toMatch(/\/api\/collections\/images\/agent\/chat$/);
        expect(JSON.parse(init?.body as string)).toEqual({
            messages: [{ role: 'user', content: 'Tag tigers' }],
            selected_sample_ids: ['s1']
        });
        expect(get(chat.active).draft).toBe('');
        expect(get(chat.active).turns).toEqual([
            {
                prompt: 'Tag tigers',
                status: 'done',
                messages: [answer],
                startedAt: expect.any(Number),
                finishedAt: expect.any(Number)
            }
        ]);
        expect(onUiActions).toHaveBeenCalledExactlyOnceWith(done.ui_actions);
    });

    it('restores two chats independently, keeps drafts, and can continue the earlier chat', async () => {
        const storage = memoryHistory();
        const fetchMock = vi.fn<typeof fetch>(async () => doneReply());
        vi.stubGlobal('fetch', fetchMock);
        const now = vi.spyOn(Date, 'now').mockReturnValue(1);
        const chat = createAgentChat('images', storage);
        await chat.ready;
        await chat.send('First', selection, noop);
        const firstId = get(chat.activeId);
        chat.setDraft('Follow-up');
        chat.newChat();
        chat.newChat();
        now.mockReturnValue(2);
        await chat.send('Second', selection, noop);
        const secondId = get(chat.activeId);
        now.mockRestore();

        await vi.waitFor(async () => {
            const records = await storage.load('images');
            expect(records.some((record) => record.activeId === secondId)).toBe(true);
        });
        const restored = createAgentChat('images', storage);
        const other = createAgentChat('other', storage);
        await Promise.all([restored.ready, other.ready]);
        expect(get(other.history)).toEqual([]);
        expect(get(restored.activeId)).toBe(secondId);
        expect(get(restored.history).map(({ id }) => id)).toEqual([secondId, firstId]);

        restored.select(firstId);
        expect(get(restored.active).draft).toBe('Follow-up');
        expect(fetchMock).toHaveBeenCalledTimes(2);
        await restored.send('Follow-up', selection, noop);
        expect(JSON.parse(fetchMock.mock.calls[2][1]?.body as string).messages).toEqual([
            { role: 'user', content: 'First' },
            answer,
            { role: 'user', content: 'Follow-up' }
        ]);
    });

    it('keeps the streamed reply and grid actions with the conversation that started it', async () => {
        const { promise, resolve } = Promise.withResolvers<Response>();
        vi.stubGlobal(
            'fetch',
            vi.fn(() => promise)
        );
        const chat = createAgentChat('images', memoryHistory());
        await chat.ready;

        const onUiActions = vi.fn(async () => {});
        const pending = chat.send('Original', selection, onUiActions);
        const originalId = get(chat.activeId);
        chat.newChat();
        chat.setDraft('Another task');

        resolve(doneReply());
        await pending;

        expect(get(chat.active).draft).toBe('Another task');
        expect(get(chat.active).turns).toEqual([]);
        chat.select(originalId);
        expect(get(chat.active).turns[0].messages).toEqual([answer]);
        expect(onUiActions).toHaveBeenCalledExactlyOnceWith(done.ui_actions);
    });

    it('restores an interrupted turn with completed outcomes and never repeats its actions', async () => {
        const storage = memoryHistory();
        const step = {
            role: 'assistant',
            tool_calls: [
                { id: 'c1', type: 'function', function: { name: 'tag_samples', arguments: '{}' } }
            ]
        };
        const result = { role: 'tool', tool_call_id: 'c1', content: '{"tagged_count":2}' };
        let closeStream = () => {};
        const stream = new ReadableStream({
            start(controller) {
                closeStream = () => controller.close();
                for (const message of [step, result]) {
                    controller.enqueue(
                        new TextEncoder().encode(
                            JSON.stringify({ type: 'message', message }) + '\n'
                        )
                    );
                }
            }
        });
        const fetchMock = vi.fn(async () => new Response(stream));
        vi.stubGlobal('fetch', fetchMock);
        const chat = createAgentChat('images', storage);
        await chat.ready;
        const onUiActions = vi.fn(async () => {});
        const pending = chat.send('Tag samples', selection, onUiActions);
        await vi.waitFor(async () => {
            const records = await storage.load('images');
            expect(
                records.find(({ conversation }) => conversation)?.conversation?.turns[0].messages
            ).toEqual([step, result]);
        });

        const restored = createAgentChat('images', storage);
        await restored.ready;
        expect(get(restored.active).turns[0]).toMatchObject({
            prompt: 'Tag samples',
            status: 'failed',
            messages: [step, result]
        });
        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(onUiActions).not.toHaveBeenCalled();
        closeStream();
        await pending;
    });

    it('keeps chatting when storage is unavailable and reports failed requests on their turn', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(
                async () =>
                    new Response(JSON.stringify({ detail: 'The AI agent is off.' }), {
                        status: 503
                    })
            )
        );
        const chat = createAgentChat('images', {
            load: async () => [],
            save: async () => {
                throw new Error('Storage unavailable');
            }
        });
        await chat.ready;
        await chat.send('Hello', selection, noop);
        expect(get(chat.active).turns[0]).toMatchObject({
            prompt: 'Hello',
            status: 'failed',
            error: 'The AI agent is off.'
        });
        expect(get(chat.storageError)).toContain('could not be saved');
    });

    it('stops a running reply and keeps the turn as stopped', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn<typeof fetch>(async (_url, init) => {
                const body = new ReadableStream<Uint8Array>({
                    start(controller) {
                        const event = { type: 'content_delta', text: 'Let me look.' };
                        controller.enqueue(new TextEncoder().encode(JSON.stringify(event) + '\n'));
                        init?.signal?.addEventListener('abort', () =>
                            controller.error(new DOMException('Aborted', 'AbortError'))
                        );
                    }
                });
                return new Response(body);
            })
        );
        const chat = createAgentChat('images', memoryHistory());
        await chat.ready;

        const sending = chat.send('Find tigers', selection, noop);
        await vi.waitFor(() => expect(get(chat.liveReply)?.text).toBe('Let me look.'));
        chat.stop();
        await sending;

        expect(get(chat.isSending)).toBe(false);
        expect(get(chat.active).turns[0]).toMatchObject({
            status: 'failed',
            error: STOPPED
        });
    });

    it('leaves a turn that failed before an answer out of the next request', async () => {
        const fetchMock = vi
            .fn<typeof fetch>()
            .mockResolvedValueOnce(new Response('{}', { status: 500 }))
            .mockResolvedValueOnce(doneReply());
        vi.stubGlobal('fetch', fetchMock);
        const chat = createAgentChat('images', memoryHistory());
        await chat.ready;

        await chat.send('Hello', selection, noop);
        await chat.send('Hello again', selection, noop);

        const [, init] = fetchMock.mock.calls[1];
        expect(JSON.parse(init?.body as string).messages).toEqual([
            { role: 'user', content: 'Hello again' }
        ]);
    });

    it('collects the live reasoning of a step until its message arrives', async () => {
        let finishStream: () => void = () => {};
        vi.stubGlobal(
            'fetch',
            vi.fn<typeof fetch>(async () => {
                const encoder = new TextEncoder();
                const line = (event: object) => encoder.encode(JSON.stringify(event) + '\n');
                const body = new ReadableStream<Uint8Array>({
                    start(controller) {
                        controller.enqueue(line({ type: 'reasoning_delta', text: '**Plan**' }));
                        controller.enqueue(line({ type: 'reasoning_delta', text: ' Tag them.' }));
                        finishStream = () => {
                            controller.enqueue(line({ type: 'message', message: answer }));
                            controller.enqueue(line(done));
                            controller.close();
                        };
                    }
                });
                return new Response(body);
            })
        );
        const chat = createAgentChat('images', memoryHistory());
        await chat.ready;

        const sending = chat.send('Tag tigers', selection, noop);
        await vi.waitFor(() => expect(get(chat.liveReply)?.reasoning).toBe('**Plan** Tag them.'));
        finishStream();
        await sending;

        expect(get(chat.liveReply)).toBeNull();
    });
});
