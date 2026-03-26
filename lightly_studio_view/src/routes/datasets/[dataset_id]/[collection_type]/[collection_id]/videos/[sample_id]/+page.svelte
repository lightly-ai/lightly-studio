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
    const { video } = useVideo({
        sampleId: data.params.sample_id
    });

    const frameNumber = data.frameNumber ? parseInt(data.frameNumber) : undefined;
    const { collection } = useCollectionWithChildren({
        collectionId: data.params.dataset_id
    });
</script>

{#if $video.isLoading}
    <Spinner />
{:else if $video.error}
    <Alert title="Error loading video">{$video.error.message}</Alert>
{:else if $video.data}
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
            <div class="grow">
                <VideoDetails
                    video={$video.data}
                    onVideoUpdate={() => $video.refetch()}
                    datasetId={data.params.dataset_id}
                    {frameNumber}
                />
            </div>
        </div>
    {:else}
        <LayoutCard className="p-4">
            <div class="flex h-full w-full flex-col space-y-4">
                {#if $collection.data}
                    <div class="flex w-full items-center">
                        <VideoDetailsBreadcrumb
                            rootCollection={$collection.data}
                            datasetId={data.params.dataset_id}
                            collectionType={data.params.collection_type}
                            sampleId={data.params.sample_id}
                        />
                    </div>
                    <Separator class="mb-4 bg-border-hard" />
                {/if}

                <VideoDetails
                    video={$video.data}
                    onVideoUpdate={() => $video.refetch()}
                    datasetId={data.params.dataset_id}
                    {frameNumber}
                />
            </div>
        </LayoutCard>
    {/if}
{/if}
