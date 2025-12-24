<script lang="ts">
    import { toast } from 'svelte-sonner';
    import { page } from '$app/state';
    import { Card, CardContent } from '$lib/components';
    import type { SampleView } from '$lib/api/lightly_studio_local';
    import { SampleType } from '$lib/api/lightly_studio_local';
    import { SampleImage } from '$lib/components';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { createQuery } from '@tanstack/svelte-query';
    import { getVideoByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';

    const {
        item,
        onUpdate,
        maxHeight = '100%'
    }: {
        item: SampleView;
        onUpdate: () => void;
        maxHeight?: string;
    } = $props();

    const { gridViewSampleRenderingStore } = useSettings();
    const { isEditingMode } = page.data.globalStorage;

    let objectFit = $derived($gridViewSampleRenderingStore); // Use store value directly
    $inspect(item);

    // Get collection to determine sample type
    const collection = $derived(page.data.collection);
    const sampleType = $derived(collection?.sample_type);

    // Fetch video data if it's a video sample to get the first frame
    const videoQuery = createQuery({
        ...getVideoByIdOptions({
            path: { sample_id: item.sample_id }
        }),
        enabled: sampleType === SampleType.VIDEO
    });

    const video = $derived($videoQuery.data);
    const firstFrameId = $derived(video?.frame?.sample_id);

    const { deleteCaption } = useDeleteCaption();

    const onDeleteCaption = async (sampleId: string) => {
        if (!item) return;

        try {
            await deleteCaption(sampleId);
            toast.success('Caption deleted successfully');
            onUpdate();
        } catch (error) {
            toast.error('Failed to delete caption. Please try again.');
            console.error('Error deleting caption:', error);
        }
    };

    const { createCaption } = useCreateCaption();

    const onCreateCaption = async (sampleId: string) => {
        try {
            await createCaption({ parent_sample_id: sampleId });
            toast.success('Caption created successfully');
            onUpdate();
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
        }
    };
</script>

<div style={`height: ${maxHeight}; max-height: ${maxHeight};`}>
    <Card className="h-full">
        <CardContent className="h-full flex min-h-0 flex-row items-center dark:[color-scheme:dark]">
            {#if sampleType === SampleType.IMAGE}
                <SampleImage sample={item} {objectFit} />
            {:else if sampleType === SampleType.VIDEO}
                {#if firstFrameId}
                    <img
                        src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${firstFrameId}`}
                        alt={item.file_path_abs ?? item.sample_id}
                        class="sample-image rounded-lg bg-black"
                        style="--object-fit: {objectFit}"
                        loading="lazy"
                    />
                {:else if $videoQuery.isPending}
                    <div class="sample-image flex items-center justify-center rounded-lg bg-black">
                        <div class="text-white">Loading...</div>
                    </div>
                {:else}
                    <div class="sample-image flex items-center justify-center rounded-lg bg-black">
                        <div class="text-white">No frame available</div>
                    </div>
                {/if}
            {:else}
                <SampleImage sample={item} {objectFit} />
            {/if}
            <div class="flex h-full w-full flex-1 flex-col overflow-auto px-4 py-2">
                {#each item.captions as caption}
                    <CaptionField
                        {caption}
                        onDeleteCaption={() => onDeleteCaption(caption.sample_id)}
                        {onUpdate}
                    />
                {/each}
                {#if $isEditingMode}
                    <button
                        type="button"
                        class="mb-2 flex h-8 items-center justify-center rounded-sm bg-card px-2 py-0 text-diffuse-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                        onclick={() => onCreateCaption(item.sample_id)}
                        data-testid="add-caption-button"
                    >
                        +
                    </button>
                {/if}
            </div>
        </CardContent>
    </Card>
</div>

<style>
    .sample-image {
        width: var(--sample-width);
        height: var(--sample-height);
        object-fit: var(--object-fit);
    }
</style>
