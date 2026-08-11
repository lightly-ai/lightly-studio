<script lang="ts">
    import type { CollectionView } from '$lib/api/lightly_studio_local';
    import { useClassifiersMenu } from '$lib/hooks/useClassifiers/useClassifiersMenu';
    import { useExportDialog } from '$lib/hooks/useExportDialog/useExportDialog';
    import { useOperatorsDialog } from '$lib/hooks/useOperatorsDialog/useOperatorsDialog';
    import { useSamplingDialog } from '$lib/hooks/useSamplingDialog/useSamplingDialog';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';

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

    const { isDialogOpen: isClassifiersDialogOpen } = useClassifiersMenu();
    const { isSamplingDialogOpen } = useSamplingDialog();
    const { isExportDialogOpen } = useExportDialog();
    const { isOperatorsDialogOpen } = useOperatorsDialog();
    const { isSettingsDialogOpen } = useSettingsDialog();

    let hasClassifierFlowLoaded = $state(false);
    let hasOperatorsMenuLoaded = $state(false);

    $effect(() => {
        if ($isClassifiersDialogOpen) hasClassifierFlowLoaded = true;
        if ($isOperatorsDialogOpen) hasOperatorsMenuLoaded = true;
    });
</script>

<!-- These menus own subsequent dialog state, so keep them mounted after their first open. -->
{#if hasClassifier && hasClassifierFlowLoaded}
    {#await import('$lib/components/FewShotClassifier/ClassifiersMenu.svelte') then { default: ClassifiersMenu }}
        <ClassifiersMenu />
    {/await}
{/if}

{#if hasSelection && $isSamplingDialogOpen}
    {#await import('$lib/components/Sampling/SamplingCombinationDialog.svelte') then { default: SamplingCombinationDialog }}
        <SamplingCombinationDialog />
    {/await}
{/if}

{#if (isImageCollection || isVideoCollection) && $isExportDialogOpen}
    {#await import('$lib/components/ExportSamples/ExportSamples.svelte') then { default: ExportSamples }}
        <ExportSamples />
    {/await}
{/if}

{#if hasOperatorsMenuLoaded}
    {#await import('$lib/components/Operator/OperatorsMenu.svelte') then { default: OperatorsMenu }}
        <OperatorsMenu />
    {/await}
{/if}

{#if $isSettingsDialogOpen}
    {#await import('$lib/components/Settings/SettingsDialog.svelte') then { default: SettingsDialog }}
        <SettingsDialog />
    {/await}
{/if}
