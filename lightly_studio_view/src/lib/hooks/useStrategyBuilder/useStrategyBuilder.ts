import { writable } from 'svelte/store';
import {
    type StrategyInstance,
    type StrategyParams,
    type StrategyType,
    STRATEGY_OPTIONS
} from './types';
import {
    cloneStrategyParams,
    createStrategyInstance,
    generateStrategyInstanceId
} from './strategyInstance';

const STRATEGY_TYPE_ORDER: Record<StrategyType, number> = Object.fromEntries(
    STRATEGY_OPTIONS.map((opt, i) => [opt.type, i])
) as Record<StrategyType, number>;

function updateStrategyInstance(
    instance: StrategyInstance,
    params: Partial<StrategyParams>
): StrategyInstance {
    return { ...instance, params: { ...instance.params, ...params } } as StrategyInstance;
}

export function useStrategyBuilder() {
    const instances = writable<StrategyInstance[]>([]);

    function addStrategy(type: StrategyType) {
        instances.update((currentInstances) => {
            const updated = [...currentInstances, createStrategyInstance(type)];
            return updated.sort(
                (a, b) => STRATEGY_TYPE_ORDER[a.type] - STRATEGY_TYPE_ORDER[b.type]
            );
        });
    }

    function removeStrategy(id: string) {
        instances.update((currentInstances) =>
            currentInstances.filter((instance) => instance.id !== id)
        );
    }

    function duplicateStrategy(id: string) {
        instances.update((currentInstances) => {
            const index = currentInstances.findIndex((instance) => instance.id === id);
            if (index < 0) {
                return currentInstances;
            }

            const source = currentInstances[index];
            const copy: StrategyInstance = {
                ...source,
                id: generateStrategyInstanceId(),
                params: cloneStrategyParams(source.type, source.params),
                isExpanded: true
            } as StrategyInstance;

            return [
                ...currentInstances.slice(0, index + 1),
                copy,
                ...currentInstances.slice(index + 1)
            ];
        });
    }

    function updateParams(id: string, params: Partial<StrategyParams>) {
        instances.update((currentInstances) =>
            currentInstances.map((instance) =>
                instance.id === id ? updateStrategyInstance(instance, params) : instance
            )
        );
    }

    function toggleExpand(id: string) {
        instances.update((currentInstances) =>
            currentInstances.map((instance) =>
                instance.id === id ? { ...instance, isExpanded: !instance.isExpanded } : instance
            )
        );
    }

    function resetStrategies() {
        instances.set([]);
    }

    return {
        instances,
        addStrategy,
        removeStrategy,
        duplicateStrategy,
        updateParams,
        toggleExpand,
        resetStrategies
    };
}
