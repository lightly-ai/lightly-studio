import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import type {
    ClassBalancingTargetDistributionMode,
    ClassBalancingTargetRow,
    StrategyInstance
} from '$lib/hooks/useStrategyBuilder';

function toApiTargetDistribution(params: {
    target_distribution_mode: ClassBalancingTargetDistributionMode;
    target_distribution: ClassBalancingTargetRow[];
}): Record<string, number> | 'uniform' | 'input' {
    if (params.target_distribution_mode !== 'dictionary') {
        return params.target_distribution_mode;
    }
    return Object.fromEntries(
        params.target_distribution.map((row) => [row.class_name, row.weight])
    );
}

export function getMetadataKey(instance: StrategyInstance): string {
    if (instance.type === 'typicality') return `typicality-${instance.id}`;
    if (instance.type === 'similarity') return `similarity-${instance.id}`;
    if (instance.type === 'metadata_weighting') return instance.params.metadata_key;
    return '';
}

export function toApiStrategy(instance: StrategyInstance): SamplingRequest['strategies'][number] {
    if (instance.type === 'diversity') {
        return {
            strategy_name: 'diversity',
            embedding_model_name: null,
            strength: instance.params.strength
        };
    }

    if (instance.type === 'deduplication') {
        return {
            strategy_name: 'deduplication',
            embedding_model_name: null,
            strength: instance.params.strength,
            stopping_condition_minimum_distance: instance.params.stopping_condition_minimum_distance
        };
    }

    if (instance.type === 'typicality' || instance.type === 'similarity') {
        return {
            strategy_name: 'weights',
            metadata_key: getMetadataKey(instance),
            strength: instance.params.strength
        };
    }

    if (instance.type === 'metadata_weighting') {
        return {
            strategy_name: 'weights',
            metadata_key: instance.params.metadata_key,
            strength: instance.params.strength
        };
    }

    if (instance.type === 'metadata_balancing') {
        return {
            strategy_name: 'metadata_balance',
            metadata_key: instance.params.metadata_key,
            target_distribution: toApiTargetDistribution(instance.params),
            strength: instance.params.strength
        };
    }

    if (instance.type === 'subpart_diversity') {
        return {
            strategy_name: 'subpart_diversity',
            embedding_model_name: null,
            annotation_source_id: instance.params.annotation_source_id || null,
            strength: instance.params.strength
        };
    }

    return {
        strategy_name: 'balance',
        target_distribution: toApiTargetDistribution(instance.params),
        annotation_source_id: instance.params.annotation_source_id || null,
        strength: instance.params.strength
    };
}
