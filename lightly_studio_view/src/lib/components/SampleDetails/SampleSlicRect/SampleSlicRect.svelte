<script lang="ts">
    import SelectClassDialog from '$lib/components/SelectClassDialog/SelectClassDialog.svelte';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { useSlicInteraction } from './useSlicInteraction.svelte';

    let {
        interactionRect = $bindable<SVGRectElement>(),
        sample,
        sampleId,
        collectionId,
        drawerStrokeColor,
        imageUrl,
        refetch,
        onFinishBrushPendingChange
    }: ReturnType<Parameters<typeof useSlicInteraction>[0]> = $props();
    const interaction = useSlicInteraction(() => ({
        sample,
        sampleId,
        collectionId,
        drawerStrokeColor,
        imageUrl,
        refetch,
        onFinishBrushPendingChange,
        interactionRect
    }));
    const { selectClassDialogOpen } = interaction;
</script>

{#each [interaction.boundaryDataUrl, interaction.strokeMaskDataUrl, interaction.hoverMaskDataUrl] as url}
    {#if url}
        <image href={url} width={sample.width} height={sample.height} />
    {/if}
{/each}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointermove={interaction.onpointermove}
    onpointerleave={interaction.onpointerleave}
    onpointerdown={interaction.onpointerdown}
    onpointerup={interaction.onpointerup}
    onpointercancel={interaction.onpointercancel}
/>
<SelectClassDialog
    bind:open={$selectClassDialogOpen}
    labels={interaction.labels.map((label) => label.annotation_label_name ?? '').filter(Boolean)}
    onConfirm={interaction.handleSelectClassDialogConfirm}
    onCancel={interaction.handleSelectClassDialogCancel}
/>
