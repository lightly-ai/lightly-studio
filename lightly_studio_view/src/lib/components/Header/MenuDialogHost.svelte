<script lang="ts">
    import { CreateSelectionDialog, ExportSamples } from '$lib/components';
    import { ClassifiersMenu } from '$lib/components/FewShotClassifier';
    import { SettingsDialog } from '$lib/components/Settings';
    import OperatorsMenu from '$lib/components/Operator/OperatorsMenu.svelte';
    import type { CollectionView } from '$lib/api/lightly_studio_local';

    let {
        isSamples = false,
        hasEmbeddingSearch = false,
        isFSCEnabled = false,
        dataset
    } = $props<{
        isSamples?: boolean;
        hasEmbeddingSearch?: boolean;
        isFSCEnabled?: boolean;
        dataset: CollectionView;
    }>();

    const hasClassifier = $derived(isSamples && hasEmbeddingSearch && isFSCEnabled);
    const isImageDataset = $derived(dataset.sample_type == 'image');
</script>

{#if hasClassifier}
    <ClassifiersMenu />
{/if}

{#if isSamples}
    <CreateSelectionDialog />
{/if}

{#if isImageDataset}
    <ExportSamples />
{/if}

<OperatorsMenu />
<SettingsDialog />
