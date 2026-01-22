<script lang="ts">
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCollection } from '$lib/hooks/useCollection/useCollection';
    import { page } from '$app/state';
    import { toast } from 'svelte-sonner';

    type SampleDetailsCaptionSegmentProps = {
        captions: CaptionView[] | undefined;
        refetch: () => void;
        collectionId: string;
        sampleId: string;
    };

    let { captions, refetch, collectionId, sampleId }: SampleDetailsCaptionSegmentProps = $props();

    const { isEditingMode } = useGlobalStorage();

    const { deleteCaption } = useDeleteCaption();
    const { createCaption } = useCreateCaption();
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = useCollection({ collectionId: datasetId });

    const handleDeleteCaption = async (sampleId: string) => {
        try {
            await deleteCaption(sampleId);
            toast.success('Caption deleted successfully');
            refetch();
        } catch (error) {
            toast.error('Failed to delete caption. Please try again.');
            console.error('Error deleting caption:', error);
        }
    };

    const onCreateCaption = async (sampleId: string) => {
        try {
            await createCaption({ parent_sample_id: sampleId });
            toast.success('Caption created successfully');
            refetch();

            if (!captions) refetchRootCollection();
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
        }
    };
</script>

<Segment title="Captions">
    <div class="flex flex-col gap-3 space-y-4">
        <div class="flex flex-col gap-2">
            {#each captions as CaptionView[] as caption}
                <CaptionField
                    {caption}
                    onDeleteCaption={() => handleDeleteCaption(caption.sample_id)}
                    onUpdate={refetch}
                />
            {/each}
            <!-- Add new caption button -->
            {#if $isEditingMode}
                <button
                    type="button"
                    class="bg-card text-diffuse-foreground hover:bg-primary hover:text-primary-foreground mb-2 flex h-8 items-center justify-center rounded-sm px-2 py-0 transition-colors"
                    onclick={() => onCreateCaption(sampleId)}
                    data-testid="add-caption-button"
                >
                    +
                </button>
            {/if}
        </div>
    </div>
</Segment>
