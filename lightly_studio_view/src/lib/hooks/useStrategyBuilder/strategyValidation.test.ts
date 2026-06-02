import { describe, expect, it } from 'vitest';
import { isStrategyInstanceValid, type StrategyInstance } from '.';

const defaultDiversity: StrategyInstance = {
    id: '1',
    type: 'diversity',
    params: { strength: 1 },
    isExpanded: true
};

const defaultTypicality: StrategyInstance = {
    id: '1',
    type: 'typicality',
    params: { strength: 1 },
    isExpanded: true
};

const defaultSimilarity: StrategyInstance = {
    id: '1',
    type: 'similarity',
    params: { query_tag_id: 'tag-abc', strength: 1 },
    isExpanded: true
};

const defaultMetadataWeighting: StrategyInstance = {
    id: '1',
    type: 'metadata_weighting',
    params: { metadata_key: 'sharpness', strength: 1 },
    isExpanded: true
};

const defaultClassBalancing: StrategyInstance = {
    id: '1',
    type: 'class_balancing',
    params: { target_distribution_mode: 'uniform', target_distribution: [], strength: 1 },
    isExpanded: true
};

describe('isStrategyInstanceValid', () => {
    describe('strength validation', () => {
        it('returns false when strength is 0', () => {
            const instance: StrategyInstance = {
                ...defaultDiversity,
                params: { strength: 0 }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns true when strength is negative', () => {
            const instance: StrategyInstance = {
                ...defaultTypicality,
                params: { strength: -1 }
            };

            expect(isStrategyInstanceValid(instance)).toBe(true);
        });

        it('returns false when strength is NaN', () => {
            const instance: StrategyInstance = {
                ...defaultDiversity,
                params: { strength: NaN }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns false when strength is Infinity', () => {
            const instance: StrategyInstance = {
                ...defaultDiversity,
                params: { strength: Infinity }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });
    });

    describe('diversity', () => {
        it('returns true when strength is valid', () => {
            expect(isStrategyInstanceValid(defaultDiversity)).toBe(true);
        });
    });

    describe('typicality', () => {
        it('returns true when strength is valid', () => {
            expect(isStrategyInstanceValid(defaultTypicality)).toBe(true);
        });
    });

    describe('similarity', () => {
        it('returns false when query_tag_id is empty', () => {
            const instance: StrategyInstance = {
                ...defaultSimilarity,
                params: { ...defaultSimilarity.params, query_tag_id: '' }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns false when query_tag_id is whitespace', () => {
            const instance: StrategyInstance = {
                ...defaultSimilarity,
                params: { ...defaultSimilarity.params, query_tag_id: '   ' }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns true when query_tag_id is set', () => {
            expect(isStrategyInstanceValid(defaultSimilarity)).toBe(true);
        });
    });

    describe('metadata_weighting', () => {
        it('returns false when metadata_key is empty', () => {
            const instance: StrategyInstance = {
                ...defaultMetadataWeighting,
                params: { ...defaultMetadataWeighting.params, metadata_key: '' }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns false when metadata_key is whitespace', () => {
            const instance: StrategyInstance = {
                ...defaultMetadataWeighting,
                params: { ...defaultMetadataWeighting.params, metadata_key: '   ' }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns true when metadata_key is set', () => {
            expect(isStrategyInstanceValid(defaultMetadataWeighting)).toBe(true);
        });
    });

    describe('class_balancing', () => {
        it('returns true for uniform target_distribution_mode regardless of distribution', () => {
            expect(isStrategyInstanceValid(defaultClassBalancing)).toBe(true);
        });

        it('returns true for input target_distribution_mode regardless of distribution', () => {
            const instance: StrategyInstance = {
                ...defaultClassBalancing,
                params: { ...defaultClassBalancing.params, target_distribution_mode: 'input' }
            };

            expect(isStrategyInstanceValid(instance)).toBe(true);
        });

        it('returns false for dictionary with empty target_distribution', () => {
            const instance: StrategyInstance = {
                ...defaultClassBalancing,
                params: {
                    ...defaultClassBalancing.params,
                    target_distribution_mode: 'dictionary',
                    target_distribution: []
                }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns false for dictionary when a row has an empty class_name', () => {
            const instance: StrategyInstance = {
                ...defaultClassBalancing,
                params: {
                    ...defaultClassBalancing.params,
                    target_distribution_mode: 'dictionary',
                    target_distribution: [{ class_name: '', weight: 1 }]
                }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns false for dictionary when a row has a whitespace class_name', () => {
            const instance: StrategyInstance = {
                ...defaultClassBalancing,
                params: {
                    ...defaultClassBalancing.params,
                    target_distribution_mode: 'dictionary',
                    target_distribution: [{ class_name: '   ', weight: 1 }]
                }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns false for dictionary when a row has a non-positive weight', () => {
            const instance: StrategyInstance = {
                ...defaultClassBalancing,
                params: {
                    ...defaultClassBalancing.params,
                    target_distribution_mode: 'dictionary',
                    target_distribution: [{ class_name: 'cat', weight: 0 }]
                }
            };

            expect(isStrategyInstanceValid(instance)).toBe(false);
        });

        it('returns true for dictionary with a valid distribution', () => {
            const instance: StrategyInstance = {
                ...defaultClassBalancing,
                params: {
                    ...defaultClassBalancing.params,
                    target_distribution_mode: 'dictionary',
                    target_distribution: [
                        { class_name: 'cat', weight: 2 },
                        { class_name: 'dog', weight: 1 }
                    ]
                }
            };

            expect(isStrategyInstanceValid(instance)).toBe(true);
        });
    });
});
