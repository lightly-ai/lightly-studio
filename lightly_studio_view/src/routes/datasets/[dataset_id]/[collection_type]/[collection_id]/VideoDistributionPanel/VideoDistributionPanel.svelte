<script lang="ts">
    import DatasetDistributionPanel from '$lib/components/DatasetDistributionPanel/DatasetDistributionPanel.svelte';
    import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';
    import type { CategoryCount } from '$lib/components/BarChart';
    import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
    import {
        useAnnotationCollectionsFilter,
        useMetadataFilters,
        useVideoFilters
    } from '$lib/hooks';
    import { buildDistributionSources } from '../distributionSources';
    import MetadataJointDistribution from '../MetadataJointDistribution/MetadataJointDistribution.svelte';
    import { selectJointMetadataKeys } from '../MetadataJointDistribution/jointSelection';
    import { buildVideoDistributionFilters } from './videoDistributionFilters';
    import { useVideoClassDistributionSource } from './useVideoClassDistributionSource.svelte';
    import { useVideoMetadataDistributionSource } from './useVideoMetadataDistributionSource.svelte';

    interface Props {
        collectionId: string;
        /** False only when annotation labels have loaded and there are none. */
        hasAnnotationClasses: boolean;
        /** Labels selected in the sidebar's LabelsMenu. */
        selectedClassNames: string[];
        onClassBarClick: (item: CategoryCount) => void;
        onClose: () => void;
        // The host keeps the bin count so that it stays when the panel closes and opens again.
        histogramBinCount: number;
    }

    let {
        collectionId,
        hasAnnotationClasses,
        selectedClassNames,
        onClassBarClick,
        onClose,
        histogramBinCount = $bindable()
    }: Props = $props();

    const { allSourcesHidden } = useAnnotationCollectionsFilter();
    const { filterParams } = useVideoFilters();
    const { metadataInfo } = useMetadataFilters();
    const filters = $derived(buildVideoDistributionFilters($filterParams));

    let activeDistributionSourceId = $state<string | undefined>(undefined);
    let activeDistributionGroupId = $state<string | undefined>(undefined);

    const classDistribution = useVideoClassDistributionSource(() => ({
        collectionId,
        filter: filters.filter,
        selectedClassNames,
        allSourcesHidden: $allSourcesHidden,
        active: activeDistributionSourceId === undefined || activeDistributionSourceId === 'classes'
    }));
    const metadataDistribution = useVideoMetadataDistributionSource(() => ({
        collectionId,
        filter: filters.filter,
        baseFilter: filters.baseFilter,
        histogramBinCount,
        activeSourceId: activeDistributionSourceId,
        activeGroupId: activeDistributionGroupId
    }));

    // The joint distribution needs two metadata fields, one for each axis.
    const jointDistributionSource = $derived<DistributionSource | null>(
        selectJointMetadataKeys($metadataInfo).length >= 2
            ? { id: 'metadata-2d', label: 'Metadata 2D', content: jointDistribution }
            : null
    );

    const distributionSources = $derived<DistributionSource[]>(
        buildDistributionSources({
            classSource: classDistribution.source,
            metadataSource: metadataDistribution.source,
            jointSource: jointDistributionSource,
            hasAnnotationClasses
        })
    );
</script>

{#snippet jointDistribution()}
    <MetadataJointDistribution {collectionId} filter={filters.filter} />
{/snippet}

<!-- Video counts support only the samples count mode, so the panel hides the count mode select. -->
<DatasetDistributionPanel
    sources={distributionSources}
    initialCountMode={AnnotationCountMode.SAMPLES}
    showCountMode={false}
    {onClose}
    onBarClick={onClassBarClick}
    onHistogramRangeSelect={metadataDistribution.onHistogramRangeSelect}
    onCategoricalValueToggle={metadataDistribution.onCategoricalValueToggle}
    onCategoricalValuesClear={metadataDistribution.onCategoricalValuesClear}
    onCategoricalRetry={metadataDistribution.onCategoricalRetry}
    {histogramBinCount}
    onHistogramBinCountChange={(binCount) => (histogramBinCount = binCount)}
    onGroupChange={(sourceId, groupId) => {
        activeDistributionSourceId = sourceId;
        activeDistributionGroupId = groupId;
    }}
/>
