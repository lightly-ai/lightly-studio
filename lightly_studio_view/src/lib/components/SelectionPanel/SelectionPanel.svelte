<script lang="ts">
    /*
     * TAGGING WORKFLOW PROTOTYPE — SelectionPanel (grid-view left panel, above Tags)
     *
     * Shown when ≥1 images are selected. Collapses (removed from DOM) when empty.
     * Coverage now reflects the actual current selection, not just tags touched in the
     * current session. Whenever the selected IDs change, we fetch tag membership for those
     * items and rebuild the coverage list.
     *
     * API patterns reused from TagCreateDialog:
     * - readImages / getAllVideos / getAllFrames / getAnnotation (load current tags)
     * - createTag / addSampleIdsToTagId (assign)
     * - removeThingIdsToTagId           (bulk remove from tag)
     */
    import { X, Plus } from '@lucide/svelte';
    import type { GridType } from '$lib/types';
    import type { TagView } from '$lib/services/types';
    import {
        createTag,
        addSampleIdsToTagId,
        getAllFrames,
        getAllVideos,
        getAnnotation,
        readImages,
        removeThingIdsToTagId
    } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { toast } from 'svelte-sonner';

    interface Props {
        collectionId: string;
        selectedSampleIds: Set<string>;
        allTags: TagView[];
        gridType: GridType;
        tagKind: 'sample' | 'annotation';
        onClear: () => void;
        /** Call after creating a new tag so TagsMenu list updates immediately. */
        loadTags: () => void;
    }

    let { collectionId, selectedSampleIds, allTags, gridType, tagKind, onClear, loadTags }: Props =
        $props();

    const { adjustTagSampleCount } = useGlobalStorage();

    // ── Tag coverage map ─────────────────────────────────────────────────────────
    // tag_id -> set of selected item IDs that currently have that tag
    let tagCoverage = $state<Record<string, Set<string>>>({});
    let isLoadingCoverage = $state(false);
    let coverageRequestId = 0;

    // Computed list: tags present on at least one selected sample
    const activeTags = $derived(
        allTags
            .map((t: TagView) => {
                const covered = tagCoverage[t.tag_id];
                if (!covered || covered.size === 0) return null;
                return { tag: t, count: covered.size };
            })
            .filter((x): x is { tag: TagView; count: number } => x !== null)
    );

    const N = $derived(selectedSampleIds.size);

    function setCoverageFromPairs(tagPairs: Array<{ itemId: string; tagId: string }>) {
        const nextCoverage: Record<string, Set<string>> = {};

        for (const { itemId, tagId } of tagPairs) {
            if (!nextCoverage[tagId]) {
                nextCoverage[tagId] = new Set<string>();
            }
            nextCoverage[tagId].add(itemId);
        }

        tagCoverage = nextCoverage;
    }

    async function loadSelectionCoverage(ids: string[]) {
        if (ids.length === 0) {
            tagCoverage = {};
            return;
        }

        const requestId = ++coverageRequestId;
        isLoadingCoverage = true;

        try {
            const tagPairs: Array<{ itemId: string; tagId: string }> = [];

            if (gridType === 'samples') {
                const response = await readImages({
                    path: { collection_id: collectionId },
                    body: { sample_ids: ids }
                });
                if (response.error) throw new Error('load images failed');

                for (const image of response.data?.data ?? []) {
                    for (const tag of image.sample.tags ?? []) {
                        tagPairs.push({ itemId: image.sample_id, tagId: tag.tag_id! });
                    }
                }
            } else if (gridType === 'videos') {
                const response = await getAllVideos({
                    path: { collection_id: collectionId },
                    body: {
                        filter: {
                            sample_filter: {
                                sample_ids: ids
                            }
                        }
                    }
                });
                if (response.error) throw new Error('load videos failed');

                for (const video of response.data?.data ?? []) {
                    for (const tag of video.sample.tags ?? []) {
                        tagPairs.push({ itemId: video.sample_id, tagId: tag.tag_id! });
                    }
                }
            } else if (gridType === 'video_frames') {
                const response = await getAllFrames({
                    path: { video_frame_collection_id: collectionId },
                    body: {
                        filter: {
                            sample_filter: {
                                sample_ids: ids
                            }
                        }
                    }
                });
                if (response.error) throw new Error('load frames failed');

                for (const frame of response.data?.data ?? []) {
                    for (const tag of frame.sample.tags ?? []) {
                        tagPairs.push({ itemId: frame.sample_id, tagId: tag.tag_id! });
                    }
                }
            } else {
                const responses = await Promise.all(
                    ids.map((id) =>
                        getAnnotation({
                            path: {
                                collection_id: collectionId,
                                annotation_id: id
                            }
                        })
                    )
                );

                for (const response of responses) {
                    if (response.error) throw new Error('load annotations failed');

                    for (const tag of response.data?.tags ?? []) {
                        tagPairs.push({ itemId: response.data.sample_id, tagId: tag.tag_id });
                    }
                }
            }

            if (requestId === coverageRequestId) {
                setCoverageFromPairs(tagPairs);
            }
        } catch {
            if (requestId === coverageRequestId) {
                tagCoverage = {};
                toast.error('Failed to load tags for the current selection.');
            }
        } finally {
            if (requestId === coverageRequestId) {
                isLoadingCoverage = false;
            }
        }
    }

    $effect(() => {
        void allTags;
        void tagKind;
        const ids = [...selectedSampleIds];
        void loadSelectionCoverage(ids);
    });

    // ── Search / assign input ────────────────────────────────────────────────────
    let assignQuery = $state('');
    let showDropdown = $state(false);
    let assignBusy = $state(false);

    const assignOptions = $derived(
        allTags.filter((t: TagView) =>
            t.name.toLowerCase().includes(assignQuery.toLowerCase())
        )
    );

    const hasExactMatch = $derived(
        allTags.some(
            (t: TagView) => t.name.toLowerCase() === assignQuery.trim().toLowerCase()
        )
    );

    function handleAssignKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            assignQuery = '';
            showDropdown = false;
        }
        if (event.key === 'Enter' && assignQuery.trim() && !hasExactMatch) {
            handleCreateAndAssign(assignQuery.trim());
        }
    }

    async function handleAssignExisting(tag: TagView) {
        assignBusy = true;
        const currentCoverage = tagCoverage[tag.tag_id] ?? new Set<string>();
        const ids = [...selectedSampleIds].filter((id) => !currentCoverage.has(id));
        if (ids.length === 0) {
            assignBusy = false;
            assignQuery = '';
            showDropdown = false;
            return;
        }
        try {
            const response = await addSampleIdsToTagId({
                path: { collection_id: collectionId, tag_id: tag.tag_id },
                body: { sample_ids: ids }
            });
            if (response.error) {
                throw new Error('assign tag failed');
            }
            // Mark all selected as having this tag
            tagCoverage = {
                ...tagCoverage,
                [tag.tag_id]: new Set([...currentCoverage, ...ids])
            };
            adjustTagSampleCount(tag.tag_id, ids.length);
        } catch {
            toast.error('Failed to assign tag. Please try again.');
            return;
        } finally {
            assignBusy = false;
        }
        assignQuery = '';
        showDropdown = false;
        loadTags();
    }

    async function handleCreateAndAssign(name: string) {
        assignBusy = true;
        const ids = [...selectedSampleIds];
        try {
            const response = await createTag({
                path: { collection_id: collectionId },
                body: { name, description: `${name} description`, kind: tagKind }
            });
            if (response.error || !response.data?.tag_id) {
                throw new Error('create tag failed');
            }
            const newTagId = response.data.tag_id;
            const assignResponse = await addSampleIdsToTagId({
                path: { collection_id: collectionId, tag_id: newTagId },
                body: { sample_ids: ids }
            });
            if (assignResponse.error) {
                throw new Error('assign created tag failed');
            }
            tagCoverage = {
                ...tagCoverage,
                [newTagId]: new Set(ids)
            };
            adjustTagSampleCount(newTagId, ids.length);
        } catch {
            toast.error('Failed to create and assign tag. Please try again.');
            return;
        } finally {
            assignBusy = false;
        }
        assignQuery = '';
        showDropdown = false;
        loadTags(); // new tag must appear in TagsMenu list
    }

    // ── [+ All] — assign remaining selected samples that don't have the tag ────
    async function assignAll(tag: TagView) {
        const alreadyHave = tagCoverage[tag.tag_id] ?? new Set<string>();
        const missing = [...selectedSampleIds].filter((id) => !alreadyHave.has(id));
        if (missing.length === 0) return;
        const response = await addSampleIdsToTagId({
            path: { collection_id: collectionId, tag_id: tag.tag_id },
            body: { sample_ids: missing }
        });
        if (response.error) {
            toast.error('Failed to assign tag. Please try again.');
            return;
        }
        tagCoverage = {
            ...tagCoverage,
            [tag.tag_id]: new Set([...selectedSampleIds])
        };
        adjustTagSampleCount(tag.tag_id, missing.length);
    }

    // ── [− All] — remove tag from all selected samples that have it ─────────────
    async function removeAll(tag: TagView) {
        const haveIt = [...(tagCoverage[tag.tag_id] ?? new Set<string>())];
        if (haveIt.length === 0) return;
        const response = await removeThingIdsToTagId({
            path: { tag_id: tag.tag_id, collection_id: collectionId } as {
                tag_id: string;
                collection_id: string;
            },
            body: { sample_ids: haveIt }
        });
        if (response.error) {
            toast.error('Failed to remove tag. Please try again.');
            return;
        }
        const updated = { ...tagCoverage };
        delete updated[tag.tag_id];
        tagCoverage = updated;
        adjustTagSampleCount(tag.tag_id, -haveIt.length);
    }
</script>

<div class="mb-3 rounded-md border border-border bg-card/60 p-3">
    <!-- Header -->
    <div class="mb-2 flex items-center justify-between">
        <span class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {N} image{N === 1 ? '' : 's'} selected
        </span>
        <button
            type="button"
            class="rounded p-0.5 text-muted-foreground hover:text-foreground"
            aria-label="Clear selection"
            onclick={onClear}
        >
            <X class="size-3.5" />
        </button>
    </div>

    <!-- Assign / create input -->
    <div class="relative mb-2">
        <div class="flex items-center gap-1 rounded-md border bg-background px-2 py-1">
            <Plus class="size-3.5 shrink-0 text-muted-foreground" />
            <!-- svelte-ignore a11y_autofocus -->
            <input
                type="text"
                placeholder="Assign or create tag..."
                bind:value={assignQuery}
                disabled={assignBusy}
                class="min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
                oninput={() => (showDropdown = true)}
                onkeydown={handleAssignKeydown}
                onfocus={() => (showDropdown = true)}
            />
        </div>
        {#if showDropdown && (assignOptions.length > 0 || (assignQuery.trim() && !hasExactMatch))}
            <div
                class="absolute left-0 top-full z-50 mt-1 max-h-44 w-full overflow-auto rounded-md border bg-popover shadow-md"
            >
                {#each assignOptions as opt (opt.tag_id)}
                    <button
                        type="button"
                        class="flex w-full items-center px-2 py-1.5 text-xs hover:bg-accent"
                        onclick={() => handleAssignExisting(opt)}
                    >
                        {opt.name}
                    </button>
                {/each}
                {#if assignQuery.trim() && !hasExactMatch}
                    <button
                        type="button"
                        class="flex w-full items-center px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent"
                        onclick={() => handleCreateAndAssign(assignQuery.trim())}
                    >
                        Create "{assignQuery.trim()}"
                    </button>
                {/if}
            </div>
        {/if}
    </div>

    <!-- Divider -->
    {#if isLoadingCoverage}
        <div class="my-2 border-t border-border"></div>
        <p class="text-xs text-muted-foreground">Loading tags for selection...</p>
    {:else if activeTags.length > 0}
        <div class="my-2 border-t border-border"></div>

        <!-- Tag coverage list -->
        <div class="space-y-1.5">
            {#each activeTags as { tag, count } (tag.tag_id)}
                {@const isAll = count === N}
                <div class="flex items-center gap-2 text-xs">
                    <!-- ● / ◑ indicator -->
                    <span
                        class="shrink-0 text-sm leading-none {isAll
                            ? 'text-primary'
                            : 'text-muted-foreground'}"
                        title={isAll ? 'All selected' : `${count}/${N} selected`}
                    >
                        {isAll ? '●' : '◑'}
                    </span>
                    <!-- Tag name + fraction -->
                    <span class="min-w-0 flex-1 truncate font-medium">{tag.name}</span>
                    {#if !isAll}
                        <span class="shrink-0 text-muted-foreground">{count}/{N}</span>
                    {/if}
                    <!-- Action buttons -->
                    <div class="flex shrink-0 items-center gap-1">
                        {#if !isAll}
                            <button
                                type="button"
                                class="rounded px-1.5 py-0.5 text-[10px] text-muted-foreground ring-1 ring-border hover:bg-accent hover:text-foreground"
                                onclick={() => assignAll(tag)}
                            >
                                + All
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="rounded px-1.5 py-0.5 text-[10px] text-muted-foreground ring-1 ring-border hover:bg-destructive/20 hover:text-destructive"
                            onclick={() => removeAll(tag)}
                        >
                            − All
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<!-- Close dropdown on outside click -->
<svelte:window
    onclick={(e) => {
        if (showDropdown && !(e.target as Element)?.closest('.relative')) {
            showDropdown = false;
        }
    }}
/>
