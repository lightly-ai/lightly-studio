<script lang="ts">
    import { CreateSelectionDialog, ExportSamples } from '$lib/components';
    import { ClassifiersMenu } from '$lib/components/FewShotClassifier';
    import { SettingsDialog } from '$lib/components/Settings';
    import OperatorsMenu from '$lib/components/Operator/OperatorsMenu.svelte';
    import { useRootDatasetOptions } from '$lib/hooks/useRootDataset/useRootDataset';

    let {
        isSamples = false,
        hasEmbeddingSearch = false,
        isFSCEnabled = false
    } = $props<{
        isSamples?: boolean;
        hasEmbeddingSearch?: boolean;
        isFSCEnabled?: boolean;
    }>();

    const hasClassifier = $derived(isSamples && hasEmbeddingSearch && isFSCEnabled);
    const { rootDataset } = useRootDatasetOptions();
    const isImageDataset = $derived($rootDataset.data?.sample_type == 'image');
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
