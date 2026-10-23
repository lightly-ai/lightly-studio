<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { Loader2 } from '@lucide/svelte';
    import AnnotationToolPopUp from '$lib/components/SampleDetails/AnnotationToolPopUp/AnnotationToolPopUp.svelte';

    type SaveAs = ComponentProps<typeof AnnotationToolPopUp>['saveAs'];

    interface Props {
        collectionId: string;
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        canSave: boolean;
        isPending: boolean;
        needsPositivePoint: boolean;
        onSave: () => void;
        onClear: () => void;
    }

    let {
        collectionId,
        saveAs,
        onSaveAsChange,
        annotationClass,
        onAnnotationClassChange,
        canSave,
        isPending,
        needsPositivePoint,
        onSave,
        onClear
    }: Props = $props();
</script>

<AnnotationToolPopUp
    title="Smart select"
    {collectionId}
    {annotationClass}
    {onAnnotationClassChange}
    {saveAs}
    {onSaveAsChange}
    {canSave}
    {onSave}
    {onClear}
>
    {#if isPending}
        <p class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 class="size-4 animate-spin" />
            Loading the preview...
        </p>
    {:else if needsPositivePoint}
        <p class="text-xs text-muted-foreground">Click the object to add a point first.</p>
    {:else}
        <p class="text-xs text-muted-foreground">
            Click to add, shift-click to remove. Or drag a box.
        </p>
    {/if}
</AnnotationToolPopUp>
