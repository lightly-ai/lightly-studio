<script lang="ts">
    import { useCollectionWithChildren, useVideo } from '$lib/hooks';
    import type { PageData } from './$types';
    import {
        LayoutCard,
        GroupsComponentsMenu,
        VideoDetails,
        Alert,
        Spinner,
        Separator
    } from '$lib/components';
    import VideoDetailsBreadcrumb from '$lib/components/VideoDetailsBreadcrumb/VideoDetailsBreadcrumb.svelte';

    const { data }: { data: PageData } = $props();
    const { data: video, isLoading, loadById, error, refetch } = useVideo();
    $effect(() => {
        loadById(data.params.sample_id);
    });
    const frameNumber = $derived(
        data.frameNumber !== undefined
            ? ((n) => (Number.isNaN(n) ? undefined : n))(parseInt(data.frameNumber, 10))
            : undefined
    );
    const { collection } = useCollectionWithChildren({
        collectionId: data.params.dataset_id
    });
</script>

{#if typeof $video !== 'undefined'}
    {#if data.params.collection_type === 'group' && data.groupId}
        <div class="flex h-full gap-4 px-4 pb-4">
            <div class="flex-none">
                <LayoutCard className="p-4 max-h-full overflow-y-auto dark:[color-scheme:dark]">
                    <GroupsComponentsMenu
                        groupId={data.groupId}
                        componentId={data.params.sample_id}
                        datasetId={data.params.dataset_id}
                        collectionId={data.params.collection_id}
                    />
                </LayoutCard>
            </div>
            <div class="min-h-0 flex-1 overflow-hidden">
                {#key `${$video.sample_id}:${frameNumber ?? ''}`}
                    <VideoDetails
                        video={$video}
                        onVideoUpdate={$refetch}
                        datasetId={data.params.dataset_id}
                        {frameNumber}
                    />
                {/key}
            </div>
        </div>
    {:else}
        <LayoutCard className="flex h-full min-h-0 flex-col overflow-hidden p-4">
            <div class="flex h-full min-h-0 w-full flex-col gap-4">
                {#if collection.data}
                    <div class="flex w-full shrink-0 items-center">
                        <VideoDetailsBreadcrumb
                            rootCollection={collection.data}
                            datasetId={data.params.dataset_id}
                            collectionType={data.params.collection_type}
                            sampleId={data.params.sample_id}
                        />
                    </div>
                    <Separator class="shrink-0 bg-border-hard" />
                {/if}
                {#key `${$video.sample_id}:${frameNumber ?? ''}`}
                    <div class="min-h-0 flex-1 overflow-hidden">
                        <VideoDetails
                            video={$video}
                            onVideoUpdate={$refetch}
                            datasetId={data.params.dataset_id}
                            {frameNumber}
                        />
                    </div>
                {/key}
            </div>
        </LayoutCard>
    {/if}
{:else if $isLoading}
    <Spinner />
{:else if $error}
    <Alert title="Error loading video">{$error.message}</Alert>
{/if}
