<script lang="ts">
    import AnnotationToolPopUp from '$lib/components/SampleDetails/AnnotationToolPopUp/AnnotationToolPopUp.svelte';
    import type { SaveAs } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';

    interface Props {
        collectionId: string;
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        canSave: boolean;
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
    <p class="text-xs text-muted-foreground">Click to add, shift-click to remove, drag to box.</p>
</AnnotationToolPopUp>
