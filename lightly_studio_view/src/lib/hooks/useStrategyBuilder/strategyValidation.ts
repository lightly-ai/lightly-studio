import { type StrategyInstance } from './types';

function isPositiveNumber(value: number): boolean {
    return Number.isFinite(value) && value > 0;
}

export function isStrategyInstanceValid(instance: StrategyInstance): boolean {
    if (!isPositiveNumber(instance.params.strength)) {
        return false;
    }

    if (instance.type === 'similarity') {
        return instance.params.query_tag_id.trim().length > 0;
    }

    if (instance.type === 'metadata_weighting') {
        return instance.params.metadata_key.trim().length > 0;
    }

    if (instance.type === 'class_balancing') {
        if (instance.params.target_distribution_mode !== 'dictionary') {
            return true;
        }
        return (
            instance.params.target_distribution.length > 0 &&
            instance.params.target_distribution.every(
                (row) => row.class_name.trim().length > 0 && isPositiveNumber(row.weight)
            )
        );
    }

    return true;
}
