<script lang="ts">
    import { CreateSelectionDialog, ExportSamples } from '$lib/components';
    import { ClassifiersMenu } from '$lib/components/FewShotClassifier';
    import { SettingsDialog } from '$lib/components/Settings';

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
</script>

{#if hasClassifier}
    <ClassifiersMenu />
{/if}

{#if isSamples}
    <CreateSelectionDialog />
    <ExportSamples />
{/if}

<SettingsDialog />
