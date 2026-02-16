<script lang="ts">
    import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
    import { routeHelpers } from '$lib/routes';
    import { getSimilarityColor } from '$lib/utils';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import SampleImage from '../SampleImage/index.svelte';
    import SelectableBox from '$lib/components/SelectableBox/SelectableBox.svelte';
    import Video from '../Video/Video.svelte';

    let {
        group,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        size,
        index,
        showCaption = false,
        isSelected = false,
        onClick,
        onKeyDown,
        style = ''
    }: {
        group: GroupView;
        size: number;
        index?: number | undefined;
        showCaption?: boolean;
        isSelected?: boolean;
        onClick?: (event: MouseEvent) => void;
        onKeyDown?: (event: KeyboardEvent) => void;
        style?: string;
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

    let videoEl: HTMLVideoElement | null = $state(null);
    let hoverTimer: ReturnType<typeof setTimeout> | null = null;
    const HOVER_DELAY = 200;
    let isHovering = false;

    async function handleVideoMouseEnter() {
        isHovering = true;
        hoverTimer = setTimeout(async () => {
            if (videoEl) {
                if (videoEl.readyState < 2) {
                    await new Promise((res) =>
                        videoEl?.addEventListener('loadeddata', res, { once: true })
                    );
                }
                if (isHovering) videoEl.play();
            }
        }, HOVER_DELAY);
    }

    function handleVideoMouseLeave() {
        isHovering = false;
        if (hoverTimer) {
            clearTimeout(hoverTimer);
            hoverTimer = null;
        }

        if (!videoEl) return;

        videoEl?.pause();
        videoEl.currentTime = 0;
    }
</script>

<div
    class="relative"
    class:sample-selected={isSelected}
    {style}
    data-testid="group-grid-item"
    data-sample-id={group.sample_id}
    data-sample-name={group.sample.file_name}
    data-index={index}
    onclick={onClick}
    onkeydown={onKeyDown}
    aria-label={`View group: ${group.sample.file_name}`}
    role="button"
    tabindex="0"
>
    <div class="absolute right-7 top-1 z-10">
        <SelectableBox onSelect={() => undefined} {isSelected} />
    </div>

    <div
        class="relative overflow-hidden rounded-lg"
        style="width: var(--sample-width); height: var(--sample-height);"
    >
        <div
            class="group-item-container relative overflow-hidden rounded-lg"
            ondblclick={handleOnDoubleClick}
            role="img"
        >
            {#if snapshot}
                {#if isVideo}
                    <!-- For video, show video player with hover-to-play -->
                    <div class="relative h-full w-full bg-black">
                        <Video
                            bind:videoEl
                            video={{ ...snapshot, sample: group.sample }}
                            frames={[]}
                            update={() => {}}
                            muted={true}
                            playsinline={true}
                            preload="metadata"
                            handleMouseEnter={handleVideoMouseEnter}
                            handleMouseLeave={handleVideoMouseLeave}
                            className="h-full w-full cursor-pointer rounded-lg object-cover shadow-md"
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

            <!-- Bottom right badges container -->
            <div class="absolute bottom-1 right-1 z-10 flex flex-col items-end gap-1">
                {#if group.similarity_score !== undefined && group.similarity_score !== null}
                    <div
                        class="flex items-center rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white backdrop-blur-sm"
                    >
                        <span
                            class="mr-1.5 block h-2 w-2 rounded-full"
                            style="background-color: {getSimilarityColor(group.similarity_score)}"
                        ></span>
                        {group.similarity_score.toFixed(2)}
                    </div>
                {/if}

                <!-- Sample count badge -->
                {#if group.sample_count > 1}
                    <div
                        class="flex items-center rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white backdrop-blur-sm"
                        title="{group.sample_count} sample{group.sample_count !== 1
                            ? 's'
                            : ''} in this group"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="mr-1 h-3 w-3"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                        >
                            <path
                                d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z"
                            />
                        </svg>
                        +{group.sample_count - 1}
                    </div>
                {/if}
            </div>

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
    </div>
</div>

<style>
    .group-item-container {
        cursor: pointer;
        background-color: black;
        width: 100%;
        height: 100%;
    }
    .sample-selected {
        outline: drop-shadow(1px 1px 1px hsl(var(--primary)))
            drop-shadow(1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px 1px 1px hsl(var(--primary)));
    }
</style>
