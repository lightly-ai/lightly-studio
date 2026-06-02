import {
    STRATEGY_DEFAULTS,
    type ClassBalancingParams,
    type ClassBalancingTargetRow,
    type StrategyInstance,
    type StrategyParamsByType,
    type StrategyType
} from './types';

function cloneClassBalancingRows(rows: ClassBalancingTargetRow[]): ClassBalancingTargetRow[] {
    return rows.map((row) => ({ ...row }));
}

export function cloneStrategyParams<T extends StrategyType>(
    type: T,
    params: StrategyParamsByType[T]
): StrategyParamsByType[T] {
    if (type === 'class_balancing') {
        return {
            ...params,
            target_distribution: cloneClassBalancingRows(
                (params as ClassBalancingParams).target_distribution
            )
        } as StrategyParamsByType[T];
    }

    return { ...params };
}

let strategyInstanceCounter = 0;

export function generateStrategyInstanceId(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }

    const fallback = strategyInstanceCounter;
    strategyInstanceCounter += 1;
    return String(fallback);
}

export function createStrategyInstance(type: StrategyType): StrategyInstance {
    return {
        id: generateStrategyInstanceId(),
        type,
        params: cloneStrategyParams(type, STRATEGY_DEFAULTS[type]),
        isExpanded: true
    } as StrategyInstance;
}
