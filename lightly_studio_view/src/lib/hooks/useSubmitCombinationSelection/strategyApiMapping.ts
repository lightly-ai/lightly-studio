import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';

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

    const targetDistribution =
        instance.params.target_distribution_mode === 'dictionary'
            ? Object.fromEntries(
                  instance.params.target_distribution.map((row) => [row.class_name, row.weight])
              )
            : instance.params.target_distribution_mode;

    return {
        strategy_name: 'balance',
        target_distribution: targetDistribution,
        annotation_source_id: instance.params.annotation_source_id || null,
        strength: instance.params.strength
    };
}
