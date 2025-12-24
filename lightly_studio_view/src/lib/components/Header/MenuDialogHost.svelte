<script lang="ts">
    import { CreateSelectionDialog, ExportSamples } from '$lib/components';
    import { ClassifiersMenu } from '$lib/components/FewShotClassifier';
    import { SettingsDialog } from '$lib/components/Settings';
    import OperatorsMenu from '$lib/components/Operator/OperatorsMenu.svelte';
    import type { CollectionView } from '$lib/api/lightly_studio_local';

    let {
        isSamples = false,
        hasEmbeddings = false,
        collection
    } = $props<{
        isSamples?: boolean;
        hasEmbeddings?: boolean;
        collection: CollectionView;
    }>();

    const hasClassifier = $derived(isSamples && hasEmbeddings);
    const isImageCollection = $derived(collection.sample_type == 'image');
</script>

{#if hasClassifier}
    <ClassifiersMenu />
{/if}

{#if isSamples}
    <CreateSelectionDialog />
{/if}

{#if isImageCollection}
    <ExportSamples />
{/if}

<OperatorsMenu />
<SettingsDialog />
