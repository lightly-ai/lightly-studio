<script lang="ts">
    import { LoaderCircle } from '@lucide/svelte';
    import { useAnnotationClassPredictionContext } from '$lib/hooks/useAnnotationClassPrediction/useAnnotationClassPrediction.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { cn, isOverlayTarget, isTextInputTarget } from '$lib/utils';

    interface Props {
        collectionId: string;
        annotations: { sample_id: string; annotation_label: { annotation_label_name: string } }[];
        refetch: () => void;
    }

    const { collectionId, annotations, refetch }: Props = $props();

    const classPrediction = useAnnotationClassPredictionContext();
    const { context: annotationLabelContext, setAnnotationLabel } = useAnnotationLabelContext();
    const { addReversibleAction, updateLastAnnotationLabel } = useGlobalStorage();
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => collectionId
    });

    const predictionState = $derived(classPrediction?.state ?? { status: 'hidden' as const });
    const predictedAnnotation = $derived(
        predictionState.status === 'ready'
            ? annotations.find((a) => a.sample_id === predictionState.annotationId)
            : undefined
    );
    const currentLabelName = $derived(predictedAnnotation?.annotation_label.annotation_label_name);

    // Selecting another annotation, or none, drops the prediction.
    $effect(() => {
        if (predictionState.status === 'hidden') return;
        if (annotationLabelContext.annotationId !== predictionState.annotationId) {
            classPrediction?.hide();
        }
    });

    const relabel = async (labelName: string) => {
        if (!predictedAnnotation || labelName === currentLabelName) return;
        addAnnotationLabelChangeToUndoStack({
            annotations: [predictedAnnotation],
            collectionId,
            addReversibleAction,
            updateAnnotations,
            refresh: refetch
        });
        await updateAnnotations([
            {
                annotation_id: predictedAnnotation.sample_id,
                collection_id: collectionId,
                label_name: labelName
            }
        ]);
        setAnnotationLabel(labelName);
        updateLastAnnotationLabel(collectionId, labelName);
        refetch();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (predictionState.status === 'hidden') return;
        if (isTextInputTarget(event.target) || isOverlayTarget(event.target)) return;
        if (event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.key === 'Escape') {
            classPrediction?.hide();
            return;
        }
        if (predictionState.status !== 'ready') return;
        if (annotationLabelContext.annotationId !== predictionState.annotationId) return;
        const entry = predictionState.top[Number(event.key) - 1];
        if (!['1', '2', '3'].includes(event.key) || !entry) return;
        event.preventDefault();
        void relabel(entry.label_name);
    };
</script>

{#if predictionState.status !== 'hidden'}
    <div
        class="pointer-events-none absolute left-1/2 top-2 z-20 -translate-x-1/2 rounded-md bg-muted px-3 py-1 text-sm shadow-md"
        data-testid="class-prediction-strip"
    >
        {#if predictionState.status === 'loading'}
            <span class="flex items-center gap-2">
                <LoaderCircle class="size-4 animate-spin" data-testid="class-prediction-spinner" />
                Predicting class…
            </span>
        {:else}
            {#each predictionState.top as entry, index (entry.annotation_label_id)}
                {#if index > 0}<span class="text-muted-foreground">{' · '}</span>{/if}
                <span class={cn(entry.label_name === currentLabelName && 'font-semibold')}>
                    <kbd class="text-muted-foreground">{index + 1}</kbd>
                    {entry.label_name}
                    {Math.round(entry.score * 100)}%
                </span>
            {/each}
        {/if}
    </div>
{/if}

<svelte:window onkeydown={handleKeyDown} />
