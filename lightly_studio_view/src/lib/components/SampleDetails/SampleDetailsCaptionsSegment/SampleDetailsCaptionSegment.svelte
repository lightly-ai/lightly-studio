<script lang="ts">
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import CreateCaptionField from '$lib/components/CaptionField/CreateCaptionField.svelte';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import { addCaptionDeleteToUndoStack } from '$lib/services/addCaptionDeleteToUndoStack';
    import { page } from '$app/state';
    import { toast } from 'svelte-sonner';

    type SampleDetailsCaptionSegmentProps = {
        captions: CaptionView[] | undefined;
        refetch: () => void;
        sampleId: string;
    };

    let { captions, refetch, sampleId }: SampleDetailsCaptionSegmentProps = $props();

    const { isEditingMode, addReversibleAction } = useGlobalStorage();

    const { deleteCaption } = useDeleteCaption();
    const { createCaption } = useCreateCaption();
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({ collectionId: datasetId })
    );

    const handleDeleteCaption = async (captionId: string) => {
        const caption = captions?.find((c) => c.sample_id === captionId);
        if (!caption) return;

        try {
            addCaptionDeleteToUndoStack({
                text: caption.text ?? '',
                parentSampleId: sampleId,
                addReversibleAction,
                createCaption,
                refetch
            });
            await deleteCaption(captionId);
            toast.success('Caption deleted successfully');
            refetch();
        } catch (error) {
            toast.error('Failed to delete caption. Please try again.');
            console.error('Error deleting caption:', error);
        }
    };

    const onCreateCaption = async (sampleId: string, text: string): Promise<boolean> => {
        try {
            await createCaption({ parent_sample_id: sampleId, text });
            toast.success('Caption created successfully');
            refetch();

            if (!captions) refetchRootCollection();
            return true;
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
            return false;
        }
    };
</script>

<Segment title="Captions">
    <div class="flex flex-col gap-3 space-y-4">
        <div class="flex flex-col gap-2">
            {#each captions as CaptionView[] as caption (caption.sample_id)}
                <CaptionField
                    {caption}
                    onDeleteCaption={() => handleDeleteCaption(caption.sample_id)}
                    onUpdate={refetch}
                />
            {/each}
            {#if $isEditingMode}
                <CreateCaptionField onCreate={(text) => onCreateCaption(sampleId, text)} />
            {/if}
        </div>
    </div>
</Segment>
