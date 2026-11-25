import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
import type { CategoricalMetadataValue } from '$lib/services/types';
import type { FilterOption } from './buildOptions';
import { getOptionLabel } from './getOptionLabel';

/** Dropdown trigger text: "All values", the one selected label, or "N selected". */
export function getSelectionSummary(
    selectedValues: CategoricalMetadataValue[],
    options: FilterOption[],
    buckets: CategoricalMetadataBucket[]
): string {
    if (selectedValues.length === 0) return 'All values';
    if (selectedValues.length > 1) return `${selectedValues.length} selected`;
    const selected = options.find(({ bucket }) => Object.is(bucket.value, selectedValues[0]))!;
    return getOptionLabel(selected, options, buckets);
}
