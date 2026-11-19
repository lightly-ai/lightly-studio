<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import { AnnotationClassSelect } from '$lib/components/SampleDetails/AnnotationClassSelect';
    import {
        AnnotationToolPopUp,
        SaveAsToggle,
        SaveButtons
    } from '$lib/components/SampleDetails/AnnotationToolPopUp';

    type SaveAs = ComponentProps<typeof SaveAsToggle>['saveAs'];

    interface Props {
        collectionId: string;
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        canSave: boolean;
        isSaving?: boolean;
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
        isSaving = false,
        isPending,
        needsPositivePoint,
        onSave,
        onClear
    }: Props = $props();
</script>

<AnnotationToolPopUp title="Smart select">
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

    {#snippet saveControls()}
        <AnnotationClassSelect
            {collectionId}
            value={annotationClass}
            onChange={onAnnotationClassChange}
            label="Annotation class"
            className="h-8"
        />
        <SaveAsToggle {saveAs} {onSaveAsChange} />
        <SaveButtons {canSave} {isSaving} {onSave} {onClear} />
    {/snippet}
</AnnotationToolPopUp>
