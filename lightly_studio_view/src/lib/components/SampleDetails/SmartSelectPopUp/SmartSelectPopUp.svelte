<script lang="ts">
    import AnnotationToolPopUp from '../AnnotationToolPopUp/AnnotationToolPopUp.svelte';
    import type { OutputType } from '../AnnotationPreview/annotationPreview.helpers';
    import { getSmartSelectHint } from './SmartSelectPopUp.helpers';

    interface Props {
        collectionId: string;
        outputType: OutputType;
        onOutputTypeChange: (outputType: OutputType) => void;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        positivePoints: boolean;
        negativePoints: boolean;
        boxes: boolean;
        canSave: boolean;
        onSave: () => void;
        onClear: () => void;
    }

    let {
        collectionId,
        outputType,
        onOutputTypeChange,
        annotationClass,
        onAnnotationClassChange,
        positivePoints,
        negativePoints,
        boxes,
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
    {outputType}
    {onOutputTypeChange}
    {canSave}
    {onSave}
    {onClear}
>
    <p class="text-xs text-muted-foreground">
        {getSmartSelectHint({ positivePoints, negativePoints, boxes })}
    </p>
</AnnotationToolPopUp>
