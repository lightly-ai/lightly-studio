import { beforeEach, describe, expect, it, vi } from 'vitest';
import { embedTextAxes } from './embedTextAxes';

const mocks = vi.hoisted(() => ({ embedText: vi.fn() }));

vi.mock('$lib/api/lightly_studio_local', () => ({ embedText: mocks.embedText }));

const EMBEDDINGS: Record<string, number[]> = {
    young: [1, 0, 0],
    old: [3, 1, 0],
    sad: [0, 2, 0],
    happy: [0, 2, 5]
};

const TEXT_AXES = {
    x: { negative: 'young', positive: 'old' },
    y: { negative: 'sad', positive: 'happy' }
};

describe('embedTextAxes', () => {
    beforeEach(() => vi.clearAllMocks());

    it('returns embed(positive) - embed(negative) per axis, one request at a time', async () => {
        let inFlight = 0;
        let maxInFlight = 0;
        mocks.embedText.mockImplementation(async ({ query }: { query: { query_text: string } }) => {
            inFlight += 1;
            maxInFlight = Math.max(maxInFlight, inFlight);
            await new Promise((resolve) => setTimeout(resolve, 0));
            inFlight -= 1;
            return { data: EMBEDDINGS[query.query_text], error: undefined };
        });

        const axes = await embedTextAxes('collection-id', TEXT_AXES);

        expect(axes).toEqual({ x: [2, 1, 0], y: [0, 0, 5] });
        expect(maxInFlight).toBe(1);
        expect(mocks.embedText).toHaveBeenCalledWith({
            path: { collection_id: 'collection-id' },
            query: { query_text: 'young', embedding_model_id: null }
        });
    });

    it('throws an Error with the server message when a text fails to embed', async () => {
        mocks.embedText.mockResolvedValue({
            data: undefined,
            error: { error: 'The embedding space cannot embed text.' }
        });

        await expect(embedTextAxes('collection-id', TEXT_AXES)).rejects.toThrow(
            'The embedding space cannot embed text.'
        );
    });
});
