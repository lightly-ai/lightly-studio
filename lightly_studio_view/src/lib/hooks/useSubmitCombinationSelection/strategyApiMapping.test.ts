import { describe, expect, it } from 'vitest';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { getMetadataKey, toApiStrategy } from './strategyApiMapping';

const defaultDiversity: StrategyInstance = {
    id: 'div-1',
    type: 'diversity',
    params: { strength: 1 },
    isExpanded: true
};

const defaultTypicality: StrategyInstance = {
    id: 'typ-1',
    type: 'typicality',
    params: { strength: 1 },
    isExpanded: true
};

const defaultSimilarity: StrategyInstance = {
    id: 'sim-1',
    type: 'similarity',
    params: { query_tag_id: 'qt-1', strength: 1 },
    isExpanded: true
};

const defaultMetadataWeighting: StrategyInstance = {
    id: 'mw-1',
    type: 'metadata_weighting',
    params: { metadata_key: 'sharpness', strength: 1 },
    isExpanded: true
};

const defaultClassBalancing: StrategyInstance = {
    id: 'cb-1',
    type: 'class_balancing',
    params: {
        annotation_source_id: '',
        target_distribution_mode: 'uniform',
        target_distribution: [],
        strength: 1
    },
    isExpanded: true
};

describe('getMetadataKey', () => {
    it('returns typicality-<id> for typicality instances', () => {
        expect(getMetadataKey({ ...defaultTypicality, id: 'abc' })).toBe('typicality-abc');
    });

    it('returns similarity-<id> for similarity instances', () => {
        expect(getMetadataKey({ ...defaultSimilarity, id: 'xyz' })).toBe('similarity-xyz');
    });

    it('returns the metadata_key field for metadata_weighting instances', () => {
        expect(getMetadataKey(defaultMetadataWeighting)).toBe('sharpness');
    });

    it('returns empty string for diversity instances', () => {
        expect(getMetadataKey(defaultDiversity)).toBe('');
    });

    it('returns empty string for class_balancing instances', () => {
        expect(getMetadataKey(defaultClassBalancing)).toBe('');
    });
});

describe('toApiStrategy', () => {
    it('maps diversity to diversity strategy with null embedding model and strength', () => {
        expect(toApiStrategy({ ...defaultDiversity, params: { strength: 2 } })).toEqual({
            strategy_name: 'diversity',
            embedding_model_name: null,
            strength: 2
        });
    });

    it('maps typicality to weights strategy using typicality-<id> as metadata key', () => {
        expect(toApiStrategy({ ...defaultTypicality, params: { strength: 1.5 } })).toEqual({
            strategy_name: 'weights',
            metadata_key: 'typicality-typ-1',
            strength: 1.5
        });
    });

    it('maps similarity to weights strategy using similarity-<id> as metadata key', () => {
        expect(toApiStrategy(defaultSimilarity)).toEqual({
            strategy_name: 'weights',
            metadata_key: 'similarity-sim-1',
            strength: 1
        });
    });

    it('maps metadata_weighting to weights strategy using the configured metadata key', () => {
        expect(
            toApiStrategy({
                ...defaultMetadataWeighting,
                params: { metadata_key: 'brightness', strength: 3 }
            })
        ).toEqual({ strategy_name: 'weights', metadata_key: 'brightness', strength: 3 });
    });

    it('maps class_balancing with uniform source to balance strategy with string target_distribution', () => {
        expect(toApiStrategy(defaultClassBalancing)).toEqual({
            strategy_name: 'balance',
            target_distribution: 'uniform',
            annotation_source_id: null,
            strength: 1
        });
    });

    it('maps class_balancing with input source to balance strategy with string target_distribution', () => {
        expect(
            toApiStrategy({
                ...defaultClassBalancing,
                params: { ...defaultClassBalancing.params, target_distribution_mode: 'input' }
            })
        ).toEqual({
            strategy_name: 'balance',
            target_distribution: 'input',
            annotation_source_id: null,
            strength: 1
        });
    });

    it('maps class_balancing with dictionary source to balance strategy converting rows to object', () => {
        expect(
            toApiStrategy({
                ...defaultClassBalancing,
                params: {
                    annotation_source_id: '',
                    target_distribution_mode: 'dictionary',
                    target_distribution: [
                        { class_name: 'cat', weight: 2 },
                        { class_name: 'dog', weight: 1 }
                    ],
                    strength: 1
                }
            })
        ).toEqual({
            strategy_name: 'balance',
            target_distribution: { cat: 2, dog: 1 },
            annotation_source_id: null,
            strength: 1
        });
    });

    it('maps class_balancing with annotation source id to balance strategy with annotation_source_id', () => {
        expect(
            toApiStrategy({
                ...defaultClassBalancing,
                params: {
                    ...defaultClassBalancing.params,
                    annotation_source_id: 'source-uuid-1'
                }
            })
        ).toEqual({
            strategy_name: 'balance',
            target_distribution: 'uniform',
            annotation_source_id: 'source-uuid-1',
            strength: 1
        });
    });
});
