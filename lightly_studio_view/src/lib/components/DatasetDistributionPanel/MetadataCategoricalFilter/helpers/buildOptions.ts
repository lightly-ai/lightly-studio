import type { CategoricalBucket } from '../../types';
import type { CategoricalMetadataValue } from '$lib/services/types';

type SelectableBucket = Exclude<CategoricalBucket, { kind: 'other' }>;
export type FilterOption = { bucket: SelectableBucket; retained: boolean };

export function buildOptions(
    buckets: CategoricalBucket[],
    selectedValues: CategoricalMetadataValue[]
): FilterOption[] {
    const selectable = buckets.filter((b): b is SelectableBucket => b.kind !== 'other');
    const returned: FilterOption[] = selectable.map((bucket) => ({ bucket, retained: false }));
    const uniqueSelected = [...new Map(selectedValues.map((v) => [JSON.stringify(v), v])).values()];
    const retained: FilterOption[] = uniqueSelected
        .filter((value) => !selectable.some((b) => Object.is(b.value, value)))
        .map((value) => ({
            bucket:
                value === null
                    ? {
                          id: JSON.stringify(['missing']),
                          kind: 'missing' as const,
                          value: null,
                          label: 'Missing',
                          count: 0
                      }
                    : {
                          id: JSON.stringify(['retained', typeof value, value]),
                          kind: 'value' as const,
                          value,
                          label: String(value),
                          count: 0
                      },
            retained: true
        }));
    return [...returned, ...retained];
}
