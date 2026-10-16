import { beforeEach, describe, expect, it, vi } from 'vitest';
import { embedTextAxes } from './embedTextAxes';

const mocks = vi.hoisted(() => ({ embedText: vi.fn() }));

vi.mock('$lib/api/lightly_studio_local', () => ({ embedText: mocks.embedText }));

// The texts have different norms, as with MobileCLIP.
const EMBEDDINGS: Record<string, number[]> = {
    young: [2, 0, 0],
    old: [0, 3, 0],
    sad: [0, 0, 4],
    happy: [3, 4, 0]
};

const TEXT_AXES = {
    x: { negative: 'young', positive: 'old' },
    y: { negative: 'sad', positive: 'happy' }
};

describe('embedTextAxes', () => {
    beforeEach(() => vi.clearAllMocks());

    it('returns unit(positive) - unit(negative) per axis, one request at a time', async () => {
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

        expect(axes).toEqual({ x: [-1, 1, 0], y: [0.6, 0.8, -1] });
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

    it('throws an Error instead of returning NaN axes for a zero embedding', async () => {
        mocks.embedText.mockResolvedValue({ data: [0, 0, 0], error: undefined });

        await expect(embedTextAxes('collection-id', TEXT_AXES)).rejects.toThrow(
            'Cannot normalize a zero-norm embedding.'
        );
    });
});
