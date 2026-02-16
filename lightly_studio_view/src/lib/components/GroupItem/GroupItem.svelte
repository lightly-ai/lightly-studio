<script lang="ts">
    import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
    import { routeHelpers } from '$lib/routes';
    import { getSimilarityColor } from '$lib/utils';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import SampleImage from '../SampleImage/index.svelte';

    let {
        group,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        size,
        index,
        showCaption = false
    }: {
        group: GroupView;
        size: number;
        index?: number | undefined;
        showCaption?: boolean;
    } = $props();

    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(group.sample.collection_id);

    function handleOnDoubleClick() {
        if (datasetId && collectionId) {
            goto(
                routeHelpers.toSamplesDetails(
                    datasetId,
                    'group',
                    collectionId,
                    group.sample_id,
                    index
                )
            );
        }
    }

    // Get the group snapshot
    const snapshot = $derived(group.group_snapshot);
    const isVideo = $derived(snapshot?.type === 'video');
    const caption = $derived(
        showCaption && group.sample.captions?.length ? group.sample.captions[0] : null
    );
</script>

<div
    class="group-item-container relative overflow-hidden rounded-lg"
    ondblclick={handleOnDoubleClick}
    role="img"
>
    {#if snapshot}
        {#if isVideo}
            <!-- For video, show the first frame as a static image -->
            <div class="relative h-full w-full bg-black">
                <img
                    src="/api/videos/sample/{snapshot.sample_id}/thumbnail"
                    alt={snapshot.file_name}
                    class="h-full w-full cursor-pointer rounded-lg object-cover shadow-md"
                />
                <!-- Video indicator badge -->
                <div
                    class="absolute left-2 top-2 z-10 rounded bg-black/70 px-2 py-1 text-xs font-medium text-white backdrop-blur-sm"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="mr-1 inline h-3 w-3"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                    >
                        <path
                            d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"
                        />
                    </svg>
                    Video
                </div>
            </div>
        {:else}
            <SampleImage
                sample={snapshot}
                class="h-full w-full cursor-pointer rounded-lg object-cover shadow-md"
            />
        {/if}
    {:else}
        <!-- Fallback for groups without samples -->
        <div
            class="flex h-full w-full items-center justify-center rounded-lg bg-gray-800 text-gray-400"
        >
            <span class="text-sm">No preview</span>
        </div>
    {/if}

    {#if group.similarity_score !== undefined && group.similarity_score !== null}
        <div
            class="absolute bottom-1 right-1 z-10 flex items-center rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white backdrop-blur-sm"
        >
            <span
                class="mr-1.5 block h-2 w-2 rounded-full"
                style="background-color: {getSimilarityColor(group.similarity_score)}"
            ></span>
            {group.similarity_score.toFixed(2)}
        </div>
    {/if}

    {#if caption}
        <div
            class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
        >
            <span class="block truncate" title={caption.text}>
                {caption.text}
            </span>
        </div>
    {/if}
</div>

<style>
    .group-item-container {
        cursor: pointer;
        background-color: black;
        width: 100%;
        height: 100%;
    }
</style>
