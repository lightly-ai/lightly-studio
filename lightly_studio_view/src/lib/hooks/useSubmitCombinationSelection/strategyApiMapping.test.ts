import { describe, expect, it } from 'vitest';
import { getMetadataKey, toApiStrategy } from './strategyApiMapping';

describe('getMetadataKey', () => {
    it('returns typicality-<id> for typicality instances', () => {
        expect(
            getMetadataKey({
                id: 'abc',
                type: 'typicality',
                params: { strength: 1 },
                isExpanded: true
            })
        ).toBe('typicality-abc');
    });

    it('returns similarity-<id> for similarity instances', () => {
        expect(
            getMetadataKey({
                id: 'xyz',
                type: 'similarity',
                params: { query_tag_id: 'qt', strength: 1 },
                isExpanded: true
            })
        ).toBe('similarity-xyz');
    });

    it('returns the metadata_key field for metadata_weighting instances', () => {
        expect(
            getMetadataKey({
                id: 'foo',
                type: 'metadata_weighting',
                params: { metadata_key: 'sharpness', strength: 1 },
                isExpanded: true
            })
        ).toBe('sharpness');
    });

    it('returns empty string for diversity instances', () => {
        expect(
            getMetadataKey({
                id: 'div',
                type: 'diversity',
                params: { strength: 1 },
                isExpanded: true
            })
        ).toBe('');
    });

    it('returns empty string for class_balancing instances', () => {
        expect(
            getMetadataKey({
                id: 'bal',
                type: 'class_balancing',
                params: { annotation_source: 'uniform', target_distribution: [], strength: 1 },
                isExpanded: true
            })
        ).toBe('');
    });
});

describe('toApiStrategy', () => {
    it('maps diversity to diversity strategy with null embedding model and strength', () => {
        expect(
            toApiStrategy({
                id: 'div-1',
                type: 'diversity',
                params: { strength: 2 },
                isExpanded: true
            })
        ).toEqual({ strategy_name: 'diversity', embedding_model_name: null, strength: 2 });
    });

    it('maps typicality to weights strategy using typicality-<id> as metadata key', () => {
        expect(
            toApiStrategy({
                id: 'typ-1',
                type: 'typicality',
                params: { strength: 1.5 },
                isExpanded: true
            })
        ).toEqual({ strategy_name: 'weights', metadata_key: 'typicality-typ-1', strength: 1.5 });
    });

    it('maps similarity to weights strategy using similarity-<id> as metadata key', () => {
        expect(
            toApiStrategy({
                id: 'sim-1',
                type: 'similarity',
                params: { query_tag_id: 'qt-1', strength: 1 },
                isExpanded: true
            })
        ).toEqual({ strategy_name: 'weights', metadata_key: 'similarity-sim-1', strength: 1 });
    });

    it('maps metadata_weighting to weights strategy using the configured metadata key', () => {
        expect(
            toApiStrategy({
                id: 'mw-1',
                type: 'metadata_weighting',
                params: { metadata_key: 'brightness', strength: 3 },
                isExpanded: true
            })
        ).toEqual({ strategy_name: 'weights', metadata_key: 'brightness', strength: 3 });
    });

    it('maps class_balancing with uniform source to balance strategy with string target_distribution', () => {
        expect(
            toApiStrategy({
                id: 'cb-1',
                type: 'class_balancing',
                params: { annotation_source: 'uniform', target_distribution: [], strength: 1 },
                isExpanded: true
            })
        ).toEqual({ strategy_name: 'balance', target_distribution: 'uniform', strength: 1 });
    });

    it('maps class_balancing with input source to balance strategy with string target_distribution', () => {
        expect(
            toApiStrategy({
                id: 'cb-2',
                type: 'class_balancing',
                params: { annotation_source: 'input', target_distribution: [], strength: 1 },
                isExpanded: true
            })
        ).toEqual({ strategy_name: 'balance', target_distribution: 'input', strength: 1 });
    });

    it('maps class_balancing with dictionary source to balance strategy converting rows to object', () => {
        expect(
            toApiStrategy({
                id: 'cb-3',
                type: 'class_balancing',
                params: {
                    annotation_source: 'dictionary',
                    target_distribution: [
                        { class_name: 'cat', weight: 2 },
                        { class_name: 'dog', weight: 1 }
                    ],
                    strength: 1
                },
                isExpanded: true
            })
        ).toEqual({
            strategy_name: 'balance',
            target_distribution: { cat: 2, dog: 1 },
            strength: 1
        });
    });
});
