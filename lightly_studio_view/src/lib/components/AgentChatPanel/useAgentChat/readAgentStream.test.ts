import { describe, expect, it } from 'vitest';
import { readAgentStream } from './readAgentStream';

const streamOf = (chunks: string[]) =>
    new ReadableStream<Uint8Array>({
        start(controller) {
            const encoder = new TextEncoder();
            for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
            controller.close();
        }
    });

const readAll = async (chunks: string[]) => {
    const events = [];
    for await (const event of readAgentStream(streamOf(chunks))) events.push(event);
    return events;
};

describe('readAgentStream', () => {
    it('reads one event per line, also when a line spans chunks', async () => {
        const events = await readAll([
            '{"type":"reasoning_delta","text":"Hm"}\n{"type":"content_',
            'delta","text":"Hi"}\n\n',
            '{"type":"turn_done","ui_actions":[]}'
        ]);

        expect(events).toEqual([
            { type: 'reasoning_delta', text: 'Hm' },
            { type: 'content_delta', text: 'Hi' },
            { type: 'turn_done', ui_actions: [] }
        ]);
    });

    it('yields a completed tool result before reporting a malformed event in the same chunk', async () => {
        const result = {
            type: 'message',
            message: { role: 'tool', tool_call_id: 'call', content: '{}' }
        };
        const events = readAgentStream(streamOf([JSON.stringify(result) + '\ninvalid\n']));

        await expect(events.next()).resolves.toMatchObject({ value: result });
        await expect(events.next()).rejects.toThrow(SyntaxError);
    });

    it('reads a multi-byte character that spans chunks', async () => {
        const bytes = new TextEncoder().encode('{"type":"content_delta","text":"é"}\n');
        const stream = new ReadableStream<Uint8Array>({
            start(controller) {
                // The "é" takes two bytes. The split puts one byte in each chunk.
                const split = bytes.indexOf(0xc3) + 1;
                controller.enqueue(bytes.slice(0, split));
                controller.enqueue(bytes.slice(split));
                controller.close();
            }
        });

        const events = [];
        for await (const event of readAgentStream(stream)) events.push(event);

        expect(events).toEqual([{ type: 'content_delta', text: 'é' }]);
    });
});
