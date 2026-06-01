import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { useStrategyBuilder } from './useStrategyBuilder';
import { STRATEGY_DEFAULTS } from './types';

describe('useStrategyBuilder', () => {
    let builder: ReturnType<typeof useStrategyBuilder>;

    beforeEach(() => {
        builder = useStrategyBuilder();
    });

    it('starts with empty instances', () => {
        expect(get(builder.instances)).toEqual([]);
    });

    it('addStrategy appends a new instance of the correct type', () => {
        builder.addStrategy('diversity');

        const instances = get(builder.instances);
        expect(instances).toHaveLength(1);
        expect(instances[0].type).toBe('diversity');
        expect(instances[0].params).toEqual(STRATEGY_DEFAULTS.diversity);
        expect(instances[0].isExpanded).toBe(true);
    });

    it('addStrategy sorts instances by defined type order', () => {
        builder.addStrategy('class_balancing');
        builder.addStrategy('diversity');
        builder.addStrategy('typicality');

        const instances = get(builder.instances);
        expect(instances[0].type).toBe('diversity');
        expect(instances[1].type).toBe('typicality');
        expect(instances[2].type).toBe('class_balancing');
    });

    it('addStrategy preserves creation order within the same type', () => {
        builder.addStrategy('diversity');
        const firstDiversityId = get(builder.instances)[0].id;
        builder.addStrategy('typicality');
        builder.addStrategy('diversity');

        const instances = get(builder.instances);
        expect(instances[0].type).toBe('diversity');
        expect(instances[0].id).toBe(firstDiversityId);
        expect(instances[1].type).toBe('diversity');
        expect(instances[2].type).toBe('typicality');
    });

    it('removeStrategy removes the matching instance and leaves others', () => {
        builder.addStrategy('diversity');
        builder.addStrategy('typicality');

        const id = get(builder.instances)[0].id;
        builder.removeStrategy(id);

        const instances = get(builder.instances);
        expect(instances).toHaveLength(1);
        expect(instances[0].type).toBe('typicality');
    });

    it('duplicateStrategy inserts a copy directly after the source', () => {
        builder.addStrategy('diversity');
        builder.addStrategy('typicality');

        const firstId = get(builder.instances)[0].id;
        builder.duplicateStrategy(firstId);

        const instances = get(builder.instances);
        expect(instances).toHaveLength(3);
        expect(instances[0].id).toBe(firstId);
        expect(instances[1].type).toBe('diversity');
        expect(instances[1].id).not.toBe(firstId);
        expect(instances[2].type).toBe('typicality');
    });

    it('duplicateStrategy is a no-op for an unknown id', () => {
        builder.addStrategy('diversity');

        builder.duplicateStrategy('does-not-exist');

        expect(get(builder.instances)).toHaveLength(1);
    });

    it('updateParams merges partial params without touching other fields', () => {
        builder.addStrategy('similarity');

        const id = get(builder.instances)[0].id;
        builder.updateParams(id, { query_tag_id: 'tag-xyz' });

        const instance = get(builder.instances)[0];
        expect(instance.params).toMatchObject({ query_tag_id: 'tag-xyz', strength: 1 });
    });

    it('toggleExpand flips isExpanded', () => {
        builder.addStrategy('diversity');

        const id = get(builder.instances)[0].id;
        expect(get(builder.instances)[0].isExpanded).toBe(true);

        builder.toggleExpand(id);
        expect(get(builder.instances)[0].isExpanded).toBe(false);

        builder.toggleExpand(id);
        expect(get(builder.instances)[0].isExpanded).toBe(true);
    });

    it('resetStrategies clears all instances', () => {
        builder.addStrategy('diversity');
        builder.addStrategy('typicality');

        builder.resetStrategies();

        expect(get(builder.instances)).toEqual([]);
    });
});
