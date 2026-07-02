import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useTextEmbedding } from './useTextEmbedding';

const mocks = vi.hoisted(() => ({
    embedText: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    embedText: mocks.embedText
}));

const setup = () => {
    const onError = vi.fn();
    const onSuccess = vi.fn();
    const text = useTextEmbedding({ getCollectionId: () => 'collection-id', onError, onSuccess });
    return { text, onError, onSuccess };
};

describe('useTextEmbedding', () => {
    beforeEach(() => vi.clearAllMocks());

    it('embeds text and calls onSuccess with trimmed query and vector', async () => {
        mocks.embedText.mockResolvedValue({ data: [1, 2, 3], error: undefined });
        const { text, onSuccess } = setup();

        await text.embed('   a yellow excavator   ');

        expect(mocks.embedText).toHaveBeenCalledWith({
            path: { collection_id: 'collection-id' },
            query: { query_text: 'a yellow excavator', embedding_model_id: null }
        });
        expect(onSuccess).toHaveBeenCalledWith({
            queryText: 'a yellow excavator',
            embedding: [1, 2, 3]
        });
    });

    it('is a no-op for empty / whitespace text', async () => {
        const { text, onSuccess } = setup();

        await text.embed('   ');

        expect(mocks.embedText).not.toHaveBeenCalled();
        expect(onSuccess).not.toHaveBeenCalled();
    });

    it('surfaces API errors via onError without calling onSuccess', async () => {
        mocks.embedText.mockResolvedValue({
            data: undefined,
            error: { error: 'embedding service unavailable' }
        });
        const { text, onError, onSuccess } = setup();

        await text.embed('cat');

        expect(onError).toHaveBeenCalledWith('embedding service unavailable');
        expect(onSuccess).not.toHaveBeenCalled();
    });

    it('toggles isEmbedding while a request is in flight', async () => {
        let resolveEmbed!: (value: { data: number[]; error: undefined }) => void;
        mocks.embedText.mockReturnValue(
            new Promise((resolve) => {
                resolveEmbed = resolve;
            })
        );
        const { text } = setup();

        expect(get(text.isEmbedding)).toBe(false);
        const pending = text.embed('cat');
        expect(get(text.isEmbedding)).toBe(true);

        resolveEmbed({ data: [1], error: undefined });
        await pending;
        expect(get(text.isEmbedding)).toBe(false);
    });

    it('keeps isEmbedding true while any concurrent request is still running', async () => {
        let resolveFirst!: (value: { data: number[]; error: undefined }) => void;
        let resolveSecond!: (value: { data: number[]; error: undefined }) => void;
        mocks.embedText
            .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
            .mockReturnValueOnce(new Promise((resolve) => (resolveSecond = resolve)));
        const { text } = setup();

        const first = text.embed('first');
        const second = text.embed('second');
        expect(get(text.isEmbedding)).toBe(true);

        resolveFirst({ data: [1], error: undefined });
        await first;
        expect(get(text.isEmbedding)).toBe(true);

        resolveSecond({ data: [2], error: undefined });
        await second;
        expect(get(text.isEmbedding)).toBe(false);
    });

    it('discards stale responses when a newer request was issued', async () => {
        let resolveFirst!: (value: { data: number[]; error: undefined }) => void;
        let resolveSecond!: (value: { data: number[]; error: undefined }) => void;
        mocks.embedText
            .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
            .mockReturnValueOnce(new Promise((resolve) => (resolveSecond = resolve)));
        const { text, onSuccess } = setup();

        const first = text.embed('first');
        const second = text.embed('second');

        resolveSecond({ data: [2], error: undefined });
        await second;
        expect(onSuccess).toHaveBeenLastCalledWith({ queryText: 'second', embedding: [2] });

        resolveFirst({ data: [1], error: undefined });
        await first;
        expect(onSuccess).toHaveBeenCalledTimes(1);
    });

    it('an empty embed call invalidates any in-flight request', async () => {
        let resolveEmbed!: (value: { data: number[]; error: undefined }) => void;
        mocks.embedText.mockReturnValue(
            new Promise((resolve) => {
                resolveEmbed = resolve;
            })
        );
        const { text, onSuccess } = setup();

        const pending = text.embed('to-clear');
        await text.embed('');

        resolveEmbed({ data: [7], error: undefined });
        await pending;

        expect(onSuccess).not.toHaveBeenCalled();
    });
});
