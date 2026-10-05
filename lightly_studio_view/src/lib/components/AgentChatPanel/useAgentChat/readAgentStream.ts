import type { AgentStreamLine } from '$lib/api/lightly_studio_local/types.gen';

/**
 * Reads the events of a streamed agent turn, one JSON object per line. A line can span
 * several chunks of the body, so the reader keeps the unfinished end of each chunk.
 */
export async function* readAgentStream(
    body: ReadableStream<Uint8Array>
): AsyncGenerator<AgentStreamLine> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        yield* parseLines(lines);
    }
    yield* parseLines([buffer + decoder.decode()]);
}

function parseLines(lines: string[]): AgentStreamLine[] {
    return lines.filter((line) => line.trim()).map((line) => JSON.parse(line) as AgentStreamLine);
}
