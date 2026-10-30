<script lang="ts">
    import DatasetDistributionPanel from '$lib/components/DatasetDistributionPanel/DatasetDistributionPanel.svelte';
    import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';
    import type { CategoryCount } from '$lib/components/BarChart';
    import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
    import { useAnnotationCollectionsFilter, useVideoFilters } from '$lib/hooks';
    import { buildDistributionSources } from '../distributionSources';
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
        // The host keeps these settings so that they stay when the panel closes and opens again.
        histogramBinCount: number;
        /** The source that the user picked, for example `classes` or `metadata`. */
        selectedSourceId: string | undefined;
        /** The group that the user picked, for example a metadata key. */
        selectedGroupId: string | undefined;
    }

    let {
        collectionId,
        hasAnnotationClasses,
        selectedClassNames,
        onClassBarClick,
        onClose,
        histogramBinCount = $bindable(),
        selectedSourceId = $bindable(),
        selectedGroupId = $bindable()
    }: Props = $props();

    const { allSourcesHidden } = useAnnotationCollectionsFilter();
    const { filterParams } = useVideoFilters();
    const filters = $derived(buildVideoDistributionFilters($filterParams));

    let activeDistributionSourceId = $state<string | undefined>(undefined);
    let activeDistributionGroupId = $state<string | undefined>(undefined);

    const classDistribution = useVideoClassDistributionSource(() => ({
        collectionId,
        filter: filters.filter,
        selectedClassNames,
        allSourcesHidden: $allSourcesHidden,
        active: activeDistributionSourceId !== 'metadata'
    }));
    const metadataDistribution = useVideoMetadataDistributionSource(() => ({
        collectionId,
        filter: filters.filter,
        baseFilter: filters.baseFilter,
        histogramBinCount,
        activeSourceId: activeDistributionSourceId,
        activeGroupId: activeDistributionGroupId
    }));

    const distributionSources = $derived<DistributionSource[]>(
        buildDistributionSources({
            classSource: classDistribution.source,
            metadataSource: metadataDistribution.source,
            hasAnnotationClasses
        })
    );
</script>

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
    bind:selectedSourceId
    bind:selectedGroupId
    onGroupChange={(sourceId, groupId) => {
        activeDistributionSourceId = sourceId;
        activeDistributionGroupId = groupId;
    }}
/>
