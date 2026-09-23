import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { getMetadataKey } from './strategyApiMapping';

export function getMetadataComputations(
    instances: StrategyInstance[]
): NonNullable<SamplingRequest['metadata_computations']> {
    return instances.flatMap<NonNullable<SamplingRequest['metadata_computations']>[number]>(
        (instance) => {
            if (instance.type === 'typicality') {
                return [{ kind: 'typicality', metadata_name: getMetadataKey(instance) }];
            }
            if (instance.type === 'similarity') {
                return [
                    {
                        kind: 'similarity',
                        metadata_name: getMetadataKey(instance),
                        query_tag_id: instance.params.query_tag_id
                    }
                ];
            }
            return [];
        }
    );
}
