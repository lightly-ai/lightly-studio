<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { useAnnotateVariant } from '$lib/hooks';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import AnnotationTargetButton from '../AnnotationTargetButton/AnnotationTargetButton.svelte';
    import AnnotationTargetRadio from '../AnnotationTargetRadio/AnnotationTargetRadio.svelte';

    // Shows the annotation source picker of the variant the `annotateVariant` switch selects.
    // Both variants take the same props.
    let {
        sourceName,
        isTarget,
        isSourceHidden,
        needsPick,
        onSetTarget
    }: ComponentProps<typeof AnnotationTargetButton> = $props();

    const { annotateVariant } = useAnnotateVariant();
    const { isEditingMode } = useGlobalStorage();
</script>

{#if $annotateVariant === 'radio'}
    <!-- Nothing can be drawn outside edit mode, so the radio only shows there. -->
    {#if $isEditingMode}
        <AnnotationTargetRadio {sourceName} {isTarget} {isSourceHidden} {needsPick} {onSetTarget} />
    {/if}
{:else}
    <AnnotationTargetButton {sourceName} {isTarget} {isSourceHidden} {needsPick} {onSetTarget} />
{/if}
