import type { SelectionRequest } from '$lib/api/lightly_studio_local/types.gen';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';

export function getMetadataKey(instance: StrategyInstance): string {
    if (instance.type === 'typicality') return `typicality-${instance.id}`;
    if (instance.type === 'similarity') return `similarity-${instance.id}`;
    if (instance.type === 'metadata_weighting') return instance.params.metadata_key;
    return '';
}

export function toApiStrategy(instance: StrategyInstance): SelectionRequest['strategies'][number] {
    if (instance.type === 'diversity') {
        return {
            strategy_name: 'diversity',
            embedding_model_name: null,
            strength: instance.params.strength
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

    const target_distribution =
        instance.params.target_distribution_mode === 'dictionary'
            ? Object.fromEntries(
                  instance.params.target_distribution.map((row) => [row.class_name, row.weight])
              )
            : instance.params.target_distribution_mode;

    return {
        strategy_name: 'balance',
        target_distribution,
        strength: instance.params.strength
    };
}
