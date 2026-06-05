<script lang="ts">
    import {
        CreateSamplingDialog,
        ExportSamples,
        SamplingCombinationDialog
    } from '$lib/components';
    import { ClassifiersMenu } from '$lib/components/FewShotClassifier';
    import { SettingsDialog } from '$lib/components/Settings';
    import OperatorsMenu from '$lib/components/Operator/OperatorsMenu.svelte';
    import { useFeatureFlags } from '$lib/hooks';
    import type { CollectionView } from '$lib/api/lightly_studio_local';

    let {
        isImages = false,
        isVideos = false,
        hasEmbeddings = false,
        collection
    } = $props<{
        isImages?: boolean;
        isVideos?: boolean;
        hasEmbeddings?: boolean;
        collection: CollectionView;
    }>();

    const hasClassifier = $derived(isImages && hasEmbeddings);
    const hasSelection = $derived(isImages || isVideos);
    const isImageCollection = $derived(collection.sample_type == 'image');
    const isVideoCollection = $derived(
        collection.sample_type == 'video' || collection.sample_type == 'video_frame'
    );

    const { featureFlags } = useFeatureFlags();
    const isCombinationSamplingEnabled = $derived($featureFlags.includes('combination_sampling'));
</script>

{#if hasClassifier}
    <ClassifiersMenu />
{/if}

{#if hasSelection}
    {#if isCombinationSamplingEnabled}
        <SamplingCombinationDialog />
    {:else}
        <CreateSamplingDialog />
    {/if}
{/if}

{#if isImageCollection || isVideoCollection}
    <ExportSamples />
{/if}

<OperatorsMenu />
<SettingsDialog />
