import { describe, expect, it } from 'vitest';
import { cloneStrategyParams, createStrategyInstance, STRATEGY_DEFAULTS } from '.';

describe('cloneStrategyParams', () => {
    it('shallow-clones non-class_balancing params', () => {
        const original = { strength: 2 };
        const clone = cloneStrategyParams('diversity', original);

        expect(clone).toEqual({ strength: 2 });
        expect(clone).not.toBe(original);
    });

    it('deep-clones class_balancing target_distribution rows', () => {
        const original = {
            target_distribution_mode: 'dictionary' as const,
            target_distribution: [{ class_name: 'cat', weight: 1 }],
            strength: 1
        };
        const clone = cloneStrategyParams('class_balancing', original);

        expect(clone.target_distribution).toEqual([{ class_name: 'cat', weight: 1 }]);
        expect(clone.target_distribution).not.toBe(original.target_distribution);
        expect(clone.target_distribution[0]).not.toBe(original.target_distribution[0]);
    });

    it('mutation of class_balancing source rows does not affect clone', () => {
        const original = {
            target_distribution_mode: 'dictionary' as const,
            target_distribution: [{ class_name: 'cat', weight: 1 }],
            strength: 1
        };
        const clone = cloneStrategyParams('class_balancing', original);

        original.target_distribution[0].class_name = 'dog';

        expect(clone.target_distribution[0].class_name).toBe('cat');
    });
});

describe('createStrategyInstance', () => {
    it('creates instance with the correct type and default params', () => {
        const instance = createStrategyInstance('diversity');

        expect(instance.type).toBe('diversity');
        expect(instance.params).toEqual(STRATEGY_DEFAULTS.diversity);
        expect(instance.params).not.toBe(STRATEGY_DEFAULTS.diversity);
    });

    it('sets isExpanded to true', () => {
        const instance = createStrategyInstance('typicality');

        expect(instance.isExpanded).toBe(true);
    });

    it('generates a unique id for each call', () => {
        const a = createStrategyInstance('diversity');
        const b = createStrategyInstance('diversity');

        expect(a.id).not.toBe(b.id);
    });
});
