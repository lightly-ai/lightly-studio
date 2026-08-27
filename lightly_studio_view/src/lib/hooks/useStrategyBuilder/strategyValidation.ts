import {
    type ClassBalancingTargetDistributionMode,
    type ClassBalancingTargetRow,
    type StrategyInstance
} from './types';

function isNonZeroFiniteNumber(value: number): boolean {
    return Number.isFinite(value) && value !== 0;
}

function isPositiveNumber(value: number): boolean {
    return Number.isFinite(value) && value > 0;
}

function isTargetDistributionValid(params: {
    target_distribution_mode: ClassBalancingTargetDistributionMode;
    target_distribution: ClassBalancingTargetRow[];
}): boolean {
    if (params.target_distribution_mode !== 'dictionary') {
        return true;
    }
    if (
        params.target_distribution.length === 0 ||
        !params.target_distribution.every(
            (row) => row.class_name.trim().length > 0 && isPositiveNumber(row.weight)
        )
    ) {
        return false;
    }
    // Duplicate rows collapse into a single target on submit, dropping part of
    // the distribution the user entered. Compared raw, like the API mapping keys them.
    const names = params.target_distribution.map((row) => row.class_name);
    return new Set(names).size === names.length;
}

export function isStrategyInstanceValid(instance: StrategyInstance): boolean {
    if (!isNonZeroFiniteNumber(instance.params.strength)) {
        return false;
    }

    if (instance.type === 'deduplication') {
        return isPositiveNumber(instance.params.stopping_condition_minimum_distance);
    }

    if (instance.type === 'similarity') {
        return instance.params.query_tag_id.trim().length > 0;
    }

    if (instance.type === 'metadata_weighting') {
        return instance.params.metadata_key.trim().length > 0;
    }

    if (instance.type === 'class_balancing') {
        return isTargetDistributionValid(instance.params);
    }

    if (instance.type === 'metadata_balancing') {
        return (
            instance.params.metadata_key.trim().length > 0 &&
            isTargetDistributionValid(instance.params)
        );
    }

    return true;
}
