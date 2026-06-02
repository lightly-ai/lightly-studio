import {
    computeSimilarityMetadata,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computeStrategyMetadata } from './computeStrategyMetadata';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    computeSimilarityMetadata: vi.fn(),
    computeTypicalityMetadata: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: { error: vi.fn(), success: vi.fn() }
}));

const { toast } = await import('svelte-sonner');

describe('computeStrategyMetadata', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls computeTypicalityMetadata with the unique instance key and reports progress', async () => {
        vi.mocked(computeTypicalityMetadata).mockResolvedValue({ data: {}, error: null } as never);
        const onProgress = vi.fn();

        const result = await computeStrategyMetadata(
            { id: 'typ-1', type: 'typicality', params: { strength: 1 }, isExpanded: true },
            'col-1',
            false,
            onProgress
        );

        expect(result).toBe(true);
        expect(onProgress).toHaveBeenCalledWith('Computing typicality metadata...');
        expect(computeTypicalityMetadata).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { embedding_model_name: null, metadata_name: 'typicality-typ-1' }
        });
    });

    it('calls computeSimilarityMetadata with the query tag id and unique instance key', async () => {
        vi.mocked(computeSimilarityMetadata).mockResolvedValue({ data: {}, error: null } as never);
        const onProgress = vi.fn();

        const result = await computeStrategyMetadata(
            {
                id: 'sim-1',
                type: 'similarity',
                params: { query_tag_id: 'qtag-1', strength: 1 },
                isExpanded: true
            },
            'col-1',
            false,
            onProgress
        );

        expect(result).toBe(true);
        expect(onProgress).toHaveBeenCalledWith('Computing similarity metadata...');
        expect(computeSimilarityMetadata).toHaveBeenCalledWith({
            path: { collection_id: 'col-1', query_tag_id: 'qtag-1' },
            body: { embedding_model_name: null, metadata_name: 'similarity-sim-1' }
        });
    });

    it('returns true without calling any API for diversity, metadata_weighting, and class_balancing', async () => {
        const onProgress = vi.fn();

        const r1 = await computeStrategyMetadata(
            { id: 'd', type: 'diversity', params: { strength: 1 }, isExpanded: true },
            'col-1',
            false,
            onProgress
        );
        const r2 = await computeStrategyMetadata(
            {
                id: 'm',
                type: 'metadata_weighting',
                params: { metadata_key: 'k', strength: 1 },
                isExpanded: true
            },
            'col-1',
            false,
            onProgress
        );
        const r3 = await computeStrategyMetadata(
            {
                id: 'b',
                type: 'class_balancing',
                params: { annotation_source: 'uniform', target_distribution: [], strength: 1 },
                isExpanded: true
            },
            'col-1',
            false,
            onProgress
        );

        expect(r1).toBe(true);
        expect(r2).toBe(true);
        expect(r3).toBe(true);
        expect(computeTypicalityMetadata).not.toHaveBeenCalled();
        expect(computeSimilarityMetadata).not.toHaveBeenCalled();
        expect(onProgress).not.toHaveBeenCalled();
    });

    it('returns false and toasts error when typicality API fails', async () => {
        vi.mocked(computeTypicalityMetadata).mockResolvedValue({
            data: undefined,
            error: { error: 'Embedding not found' }
        } as never);

        const result = await computeStrategyMetadata(
            { id: 'typ-2', type: 'typicality', params: { strength: 1 }, isExpanded: true },
            'col-1',
            false,
            vi.fn()
        );

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to compute typicality metadata: Embedding not found'
        );
    });

    it('returns false and toasts error when similarity API fails', async () => {
        vi.mocked(computeSimilarityMetadata).mockResolvedValue({
            data: undefined,
            error: { error: 'Tag not found' }
        } as never);

        const result = await computeStrategyMetadata(
            {
                id: 'sim-2',
                type: 'similarity',
                params: { query_tag_id: 'qt', strength: 1 },
                isExpanded: true
            },
            'col-1',
            false,
            vi.fn()
        );

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to compute similarity metadata: Tag not found'
        );
    });

    it('blocks similarity on video collections without calling the API', async () => {
        const result = await computeStrategyMetadata(
            {
                id: 'sim-3',
                type: 'similarity',
                params: { query_tag_id: 'qt', strength: 1 },
                isExpanded: true
            },
            'col-1',
            true,
            vi.fn()
        );

        expect(result).toBe(false);
        expect(computeSimilarityMetadata).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalledWith(
            'Similarity is only available for image collections.'
        );
    });
});
