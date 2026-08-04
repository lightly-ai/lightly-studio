import type { CategoricalBucket } from '../../types';
import type { FilterOption } from './buildOptions';

export function getOptionLabel(
    option: FilterOption,
    options: FilterOption[],
    buckets: CategoricalBucket[]
): string {
    const hasMissing = options.some(({ bucket }) => bucket.kind === 'missing');
    const hasOtherAggregate = buckets.some((bucket) => bucket.kind === 'other');
    if (
        option.bucket.kind === 'missing' &&
        options.some(({ bucket }) => bucket.value === 'Missing')
    ) {
        return 'Missing (no value)';
    }
    if (option.bucket.kind === 'value' && option.bucket.value === 'Missing' && hasMissing) {
        return 'Missing (value)';
    }
    if (option.bucket.kind === 'value' && option.bucket.value === 'Other' && hasOtherAggregate) {
        return 'Other (value)';
    }
    return option.bucket.label;
}
