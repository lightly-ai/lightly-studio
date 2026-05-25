import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useStrategyBuilder } from './useStrategyBuilder';

describe('useStrategyBuilder', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('adds a strategy with the expected defaults', () => {
        const builder = useStrategyBuilder();

        builder.addStrategy('diversity');

        expect(get(builder.instances)).toEqual([
            expect.objectContaining({
                type: 'diversity',
                isExpanded: true,
                params: {
                    embedding_model_name: '',
                    strength: 1
                }
            })
        ]);
    });

    it('creates distinct instances when the same strategy is added twice', () => {
        const builder = useStrategyBuilder();

        builder.addStrategy('typicality');
        builder.addStrategy('typicality');

        const instances = get(builder.instances);

        expect(instances).toHaveLength(2);
        expect(instances[0].id).not.toBe(instances[1].id);
    });

    it('removes only the matching instance', () => {
        const builder = useStrategyBuilder();

        builder.addStrategy('diversity');
        builder.addStrategy('similarity');

        const [first, second] = get(builder.instances);
        builder.removeStrategy(first.id);

        expect(get(builder.instances)).toEqual([second]);
    });

    it('duplicates a strategy immediately after the original', () => {
        const builder = useStrategyBuilder();

        builder.addStrategy('metadata_weighting');
        const [instance] = get(builder.instances);
        builder.updateParams(instance.id, { metadata_key: 'weather', strength: 2 });
        builder.duplicateStrategy(instance.id);

        const [original, duplicate] = get(builder.instances);

        expect(original.params).toEqual({
            metadata_key: 'weather',
            strength: 2
        });
        expect(duplicate.params).toEqual(original.params);
        expect(duplicate.id).not.toBe(original.id);
    });

    it('updates only the matching strategy params', () => {
        const builder = useStrategyBuilder();

        builder.addStrategy('diversity');
        builder.addStrategy('typicality');

        const [diversity, typicality] = get(builder.instances);
        builder.updateParams(diversity.id, { embedding_model_name: 'mobileclip', strength: 3 });

        const [updatedDiversity, unchangedTypicality] = get(builder.instances);

        expect(updatedDiversity.params).toEqual({
            embedding_model_name: 'mobileclip',
            strength: 3
        });
        expect(unchangedTypicality).toEqual(typicality);
    });

    it('toggles the expanded state only for the matching instance', () => {
        const builder = useStrategyBuilder();

        builder.addStrategy('diversity');
        builder.addStrategy('similarity');

        const [first, second] = get(builder.instances);
        builder.toggleExpand(second.id);

        const [unchanged, updated] = get(builder.instances);

        expect(unchanged.isExpanded).toBe(first.isExpanded);
        expect(updated.isExpanded).toBe(false);
    });

    it('resets the strategy list', () => {
        const builder = useStrategyBuilder();

        builder.addStrategy('diversity');
        builder.addStrategy('class_balancing');
        builder.resetStrategies();

        expect(get(builder.instances)).toEqual([]);
    });
});
