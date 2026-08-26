import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';

interface BuildDistributionSourcesParams {
    /** The annotation-classes source, built regardless of whether classes exist. */
    classSource: DistributionSource;
    /** The metadata source, or null when the dataset has no metadata fields. */
    metadataSource: DistributionSource | null;
    /**
     * Whether the dataset has any annotation classes at all. False only once
     * annotation labels have loaded and come back empty — not while loading,
     * and not just because the current filters happen to hide every class.
     */
    hasAnnotationClasses: boolean;
}

/**
 * Assembles the distribution panel's source list. The class-labels source is
 * dropped when the dataset has no annotation classes at all and there's a
 * metadata source to show instead — otherwise the source picker would offer
 * an "Annotation classes" option that can never show anything.
 */
export function buildDistributionSources({
    classSource,
    metadataSource,
    hasAnnotationClasses
}: BuildDistributionSourcesParams): DistributionSource[] {
    if (!hasAnnotationClasses && metadataSource) return [metadataSource];
    return metadataSource ? [classSource, metadataSource] : [classSource];
}
