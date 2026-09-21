<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import AnnotationToolPopUp from '../AnnotationToolPopUp/AnnotationToolPopUp.svelte';

    interface Props {
        collectionId: string;
        outputType: 'mask' | 'box';
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        onOutputTypeChange: (outputType: 'mask' | 'box') => void;
        canSave: boolean;
        onSave: () => void;
        onStartFresh: () => void;
    }

    let {
        collectionId,
        outputType,
        annotationClass,
        onAnnotationClassChange,
        onOutputTypeChange,
        canSave,
        onSave,
        onStartFresh
    }: Props = $props();
    const { setLastAnnotationOutputType } = useGlobalStorage();
    const select = (value: 'mask' | 'box') => {
        onOutputTypeChange(value);
        setLastAnnotationOutputType(value);
    };
</script>

<AnnotationToolPopUp
    title="Smart select"
    {collectionId}
    {annotationClass}
    {onAnnotationClassChange}
    {outputType}
    onOutputTypeChange={select}
    {canSave}
    {onSave}
    onClear={onStartFresh}
>
    <p class="text-xs text-muted-foreground">Click to add, shift-click to remove, drag to box.</p>
</AnnotationToolPopUp>
