<script lang="ts">
    import { CreateSelectionDialog, ExportSamples } from '$lib/components';
    import { ClassifiersMenu } from '$lib/components/FewShotClassifier';
    import { SettingsDialog } from '$lib/components/Settings';
    import OperatorsMenu from '$lib/components/Operator/OperatorsMenu.svelte';
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
</script>

{#if hasClassifier}
    <ClassifiersMenu />
{/if}

{#if hasSelection}
    <CreateSelectionDialog />
{/if}

{#if isImageCollection || isVideoCollection}
    <ExportSamples />
{/if}

<OperatorsMenu />
<SettingsDialog />
