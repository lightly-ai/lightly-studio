<script lang="ts">
    /*
     * TAGGING WORKFLOW PROTOTYPE — TagsMenu (grid-view left panel)
     *
     * New in this version (2026-04-02):
     * - Persistent search/create input at top (hidden when images are selected —
     *   SelectionPanel takes over in that case).
     * - Typing filters tag rows in real time; "Create xyz" appears when no exact match.
     * - Creating a tag with 0 images selected adds a row with count 0.
     * - Count badge on each row (starts at 0; updated via useGlobalStorage.tagSampleCounts
     *   after assign/remove operations).
     * - ⋯ hover menu per row → Rename (inline input, Enter=save, Esc=cancel,
     *   duplicate validation) and Delete (confirmation dialog, clears filter if active).
     *
     * API patterns reused from TagCreateDialog:
     * - createTag({ path:{collection_id}, body:{name,kind} })
     * - updateTag({ path:{collection_id,tag_id}, body:{name} })
     * - deleteTag({ path:{tag_id} })
     */
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Tags as TagsIcon, MoreHorizontal, Check, X } from '@lucide/svelte';
    import { Checkbox } from '$lib/components';
    import type { GridType } from '$lib/types';
    import type { TagView } from '$lib/services/types';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        createTag,
        updateTag,
        deleteTag,
        addSampleIdsToTagId,
        getAllFrames,
        getAllVideos,
        getAnnotation,
        readImages
    } from '$lib/api/lightly_studio_local';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Button } from '$lib/components/ui/button/index.js';
    import { Input } from '$lib/components/ui/input/index.js';
    import { toast } from 'svelte-sonner';

    let { collection_id, gridType }: { collection_id: string; gridType: GridType } = $props();

    const tagKind = $derived(
        (['samples', 'videos', 'video_frames'] as GridType[]).includes(gridType)
            ? ('sample' as const)
            : ('annotation' as const)
    );

    const { tags, tagsSelected, tagSelectionToggle, loadTags } = $derived(
        useTags({ collection_id, kind: [tagKind] })
    );

    const {
        tagSampleCounts,
        adjustTagSampleCount,
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds
    } = useGlobalStorage();

    // Whether ANY items are currently selected (hides the search input per spec).
    // Samples grids use selectedSampleIds; annotation grids use selectedSampleAnnotationCropIds.
    const selectedSampleIds = $derived(getSelectedSampleIds(collection_id));
    const hasSelection = $derived(
        tagKind === 'annotation'
            ? ($selectedSampleAnnotationCropIds[collection_id]?.size ?? 0) > 0
            : $selectedSampleIds.size > 0
    );
    const selectedIds = $derived(
        tagKind === 'annotation'
            ? ($selectedSampleAnnotationCropIds[collection_id] ?? new Set<string>())
            : $selectedSampleIds
    );

    // ── Selection assignment input ───────────────────────────────────────────────
    let searchQuery = $state('');
    let assignBusy = $state(false);
    let showAssignDropdown = $state(false);
    let selectionTagCoverage = $state<Record<string, Set<string>>>({});
    let coverageRequestId = 0;

    async function loadSelectionCoverage(ids: string[]) {
        if (ids.length === 0) {
            selectionTagCoverage = {};
            return;
        }

        const requestId = ++coverageRequestId;
        const nextCoverage: Record<string, Set<string>> = {};

        try {
            if (gridType === 'samples') {
                const response = await readImages({
                    path: { collection_id },
                    body: { sample_ids: ids }
                });
                if (response.error) throw new Error('load images failed');

                for (const image of response.data?.data ?? []) {
                    for (const tag of image.sample.tags ?? []) {
                        nextCoverage[tag.tag_id!] ??= new Set<string>();
                        nextCoverage[tag.tag_id!].add(image.sample_id);
                    }
                }
            } else if (gridType === 'videos') {
                const response = await getAllVideos({
                    path: { collection_id },
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
                        nextCoverage[tag.tag_id!] ??= new Set<string>();
                        nextCoverage[tag.tag_id!].add(video.sample_id);
                    }
                }
            } else if (gridType === 'video_frames') {
                const response = await getAllFrames({
                    path: { video_frame_collection_id: collection_id },
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
                        nextCoverage[tag.tag_id!] ??= new Set<string>();
                        nextCoverage[tag.tag_id!].add(frame.sample_id);
                    }
                }
            } else {
                const responses = await Promise.all(
                    ids.map((id) =>
                        getAnnotation({
                            path: {
                                collection_id,
                                annotation_id: id
                            }
                        })
                    )
                );

                for (const response of responses) {
                    if (response.error) throw new Error('load annotations failed');

                    for (const tag of response.data?.tags ?? []) {
                        nextCoverage[tag.tag_id] ??= new Set<string>();
                        nextCoverage[tag.tag_id].add(response.data.sample_id);
                    }
                }
            }

            if (requestId === coverageRequestId) {
                selectionTagCoverage = nextCoverage;
            }
        } catch {
            if (requestId === coverageRequestId) {
                selectionTagCoverage = {};
            }
        }
    }

    $effect(() => {
        void loadSelectionCoverage([...selectedIds]);
    });

    const filteredTags: TagView[] = $derived($tags);
    const assignOptions: TagView[] = $derived(
        searchQuery.trim()
            ? $tags.filter((t: TagView) =>
                  t.name.toLowerCase().includes(searchQuery.toLowerCase())
              )
            : $tags
    );

    const hasExactMatch = $derived(
        $tags.some((t: TagView) => t.name.toLowerCase() === searchQuery.trim().toLowerCase())
    );

    async function handleCreateFromSearch() {
        const name = searchQuery.trim();
        if (!name || hasExactMatch) return;
        if (!hasSelection) return;
        assignBusy = true;
        const response = await createTag({
            path: { collection_id },
            body: { name, description: `${name} description`, kind: tagKind }
        });
        if (response.error || !response.data?.tag_id) {
            assignBusy = false;
            toast.error('Failed to create tag. Please try again.');
            return;
        }
        const ids = [...selectedIds];
        const assignResponse = await addSampleIdsToTagId({
            path: { collection_id, tag_id: response.data.tag_id },
            body: { sample_ids: ids }
        });
        assignBusy = false;
        if (assignResponse.error) {
            toast.error('Failed to assign tag. Please try again.');
            return;
        }
        adjustTagSampleCount(response.data.tag_id, ids.length);
        selectionTagCoverage = {
            ...selectionTagCoverage,
            [response.data.tag_id]: new Set(ids)
        };
        searchQuery = '';
        showAssignDropdown = false;
        loadTags();
    }

    function handleSearchKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            const exactMatch = $tags.find(
                (t: TagView) => t.name.toLowerCase() === searchQuery.trim().toLowerCase()
            );
            if (exactMatch && hasSelection) {
                void handleAssignExisting(exactMatch);
                return;
            }
            void handleCreateFromSearch();
        }
        if (event.key === 'Escape') {
            searchQuery = '';
            showAssignDropdown = false;
        }
    }

    async function handleAssignExisting(tag: TagView) {
        if (!hasSelection) return;
        assignBusy = true;
        const currentCoverage = selectionTagCoverage[tag.tag_id] ?? new Set<string>();
        const ids = [...selectedIds].filter((id) => !currentCoverage.has(id));
        if (ids.length === 0) {
            assignBusy = false;
            searchQuery = '';
            showAssignDropdown = false;
            return;
        }
        const response = await addSampleIdsToTagId({
            path: { collection_id, tag_id: tag.tag_id },
            body: { sample_ids: ids }
        });
        assignBusy = false;
        if (response.error) {
            toast.error('Failed to assign tag. Please try again.');
            return;
        }
        selectionTagCoverage = {
            ...selectionTagCoverage,
            [tag.tag_id]: new Set([...currentCoverage, ...ids])
        };
        adjustTagSampleCount(tag.tag_id, ids.length);
        searchQuery = '';
        showAssignDropdown = false;
        loadTags();
    }

    // ── ⋯ Context menu ──────────────────────────────────────────────────────────
    let openMenuTagId = $state<string | null>(null);

    function toggleMenu(tagId: string, event: MouseEvent) {
        event.stopPropagation();
        openMenuTagId = openMenuTagId === tagId ? null : tagId;
    }

    function closeMenu() {
        openMenuTagId = null;
    }

    // ── Rename ───────────────────────────────────────────────────────────────────
    let renamingTagId = $state<string | null>(null);
    let renameValue = $state('');
    let renameError = $state('');

    function startRename(tagId: string, currentName: string) {
        closeMenu();
        renamingTagId = tagId;
        renameValue = currentName;
        renameError = '';
    }

    function cancelRename() {
        renamingTagId = null;
        renameValue = '';
        renameError = '';
    }

    async function commitRename(tagId: string) {
        const trimmed = renameValue.trim();
        if (!trimmed) {
            renameError = 'Tag name cannot be empty';
            return;
        }
        const currentTag = $tags.find((t: TagView) => t.tag_id === tagId);
        if (!currentTag) {
            renameError = 'Tag not found';
            return;
        }
        const duplicate = $tags.find(
            (t: TagView) => t.tag_id !== tagId && t.name.toLowerCase() === trimmed.toLowerCase()
        );
        if (duplicate) {
            renameError = `Tag '${trimmed}' already exists`;
            return;
        }
        const response = await updateTag({
            path: { collection_id, tag_id: tagId },
            body: {
                name: trimmed,
                description: currentTag.description ?? '',
                kind: currentTag.kind
            }
        });
        if (response.error) {
            renameError = 'Failed to rename tag';
            return;
        }
        cancelRename();
        loadTags();
    }

    function handleRenameKeydown(event: KeyboardEvent, tagId: string) {
        if (event.key === 'Enter') commitRename(tagId);
        if (event.key === 'Escape') cancelRename();
    }

    // ── Delete ───────────────────────────────────────────────────────────────────
    let deletingTag = $state<{ tag_id: string; name: string } | null>(null);

    function openDeleteDialog(tagId: string, name: string) {
        closeMenu();
        deletingTag = { tag_id: tagId, name };
    }

    async function confirmDelete() {
        if (!deletingTag) return;
        const { tag_id } = deletingTag;
        if ($tagsSelected.has(tag_id)) {
            tagSelectionToggle(tag_id);
        }
        const response = await deleteTag({
            path: { tag_id, collection_id } as { tag_id: string; collection_id: string }
        });
        if (response.error) {
            toast.error('Failed to delete tag. Please try again.');
            return;
        }
        deletingTag = null;
        loadTags();
    }

    const deleteTagSampleCount = $derived(
        deletingTag ? ($tagSampleCounts[deletingTag.tag_id] ?? 0) : 0
    );
</script>

<!-- Close context menu / assignment dropdown on outside click -->
<svelte:window
    onclick={(event) => {
        closeMenu();
        if (showAssignDropdown && !(event.target as Element)?.closest('.relative')) {
            showAssignDropdown = false;
        }
    }}
/>

<Segment title="Tags" icon={TagsIcon}>
    <div class="mb-3 w-full space-y-1">
        <!-- Tag rows -->
        <div class="space-y-1">
            {#each filteredTags as tag (tag.tag_id)}
                <div class="group flex items-center justify-between py-0.5" data-testid="tag-menu-item">
                    {#if renamingTagId === tag.tag_id}
                        <!-- Inline rename -->
                        <div class="flex flex-1 flex-col gap-0.5">
                            <!-- svelte-ignore a11y_autofocus -->
                            <input
                                type="text"
                                bind:value={renameValue}
                                autofocus
                                class="flex-1 rounded border border-primary bg-transparent px-1 text-xs outline-none"
                                onkeydown={(e) => handleRenameKeydown(e, tag.tag_id)}
                                onblur={cancelRename}
                            />
                            {#if renameError}
                                <span class="text-xs text-destructive">{renameError}</span>
                            {/if}
                        </div>
                        <div class="flex shrink-0 items-center gap-1 pl-1">
                            <button
                                type="button"
                                onmousedown={(e) => {
                                    e.preventDefault();
                                    commitRename(tag.tag_id);
                                }}
                                class="text-muted-foreground hover:text-foreground"
                                aria-label="Save"
                            >
                                <Check class="size-3" />
                            </button>
                            <button
                                type="button"
                                onmousedown={(e) => {
                                    e.preventDefault();
                                    cancelRename();
                                }}
                                class="text-muted-foreground hover:text-foreground"
                                aria-label="Cancel"
                            >
                                <X class="size-3" />
                            </button>
                        </div>
                    {:else}
                        <!-- Normal row: checkbox + count badge + ⋯ menu -->
                        <div class="flex min-w-0 flex-1 items-center space-x-2">
                            <Checkbox
                                name={tag.tag_id}
                                isChecked={$tagsSelected.has(tag.tag_id)}
                                label={tag.name}
                                onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                            />
                        </div>
                        <div class="flex shrink-0 items-center gap-1 pl-1">
                            <!-- Count badge — only shown when we have a known count > 0 -->
                            {#if ($tagSampleCounts[tag.tag_id] ?? 0) > 0}
                                <span
                                    class="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                                >
                                    {$tagSampleCounts[tag.tag_id]}
                                </span>
                            {/if}
                            <!-- ⋯ context menu trigger -->
                            <div class="relative">
                                <button
                                    type="button"
                                    class="rounded p-0.5 text-muted-foreground opacity-0 transition group-hover:opacity-100 hover:bg-accent hover:text-foreground"
                                    aria-label="Tag options"
                                    onclick={(e) => toggleMenu(tag.tag_id, e)}
                                >
                                    <MoreHorizontal class="size-3.5" />
                                </button>
                                {#if openMenuTagId === tag.tag_id}
                                    <div
                                        class="absolute right-0 top-full z-50 mt-1 min-w-[110px] rounded-md border bg-popover py-1 shadow-md"
                                        role="menu"
                                    >
                                        <button
                                            type="button"
                                            role="menuitem"
                                            class="flex w-full items-center px-3 py-1.5 text-xs hover:bg-accent"
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                startRename(tag.tag_id, tag.name);
                                            }}
                                        >
                                            Rename
                                        </button>
                                        <button
                                            type="button"
                                            role="menuitem"
                                            class="flex w-full items-center px-3 py-1.5 text-xs text-destructive hover:bg-accent"
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                openDeleteDialog(tag.tag_id, tag.name);
                                            }}
                                        >
                                            Delete tag
                                        </button>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/if}
                </div>
            {:else}
                <p class="text-xs text-muted-foreground">No tags yet</p>
            {/each}
        </div>

        <!-- Selection assign / create input -->
        <div class="relative pt-2">
            <Input
                type="text"
                placeholder="Assign tag to selection"
                bind:value={searchQuery}
                onkeydown={handleSearchKeydown}
                oninput={() => (showAssignDropdown = true)}
                onfocus={() => (showAssignDropdown = true)}
                onblur={() => {
                    setTimeout(() => {
                        showAssignDropdown = false;
                    }, 100);
                }}
                class="h-8 text-xs disabled:opacity-60"
                disabled={!hasSelection || assignBusy}
            />
            {#if showAssignDropdown && hasSelection && (assignOptions.length > 0 || (searchQuery.trim() && !hasExactMatch))}
                <div
                    class="absolute left-0 top-full z-50 mt-1 max-h-44 w-full overflow-auto rounded-md border bg-popover shadow-md"
                >
                    {#each assignOptions as tag (tag.tag_id)}
                        <button
                            type="button"
                            class="flex w-full items-center px-2 py-1.5 text-xs hover:bg-accent"
                            onclick={() => handleAssignExisting(tag)}
                        >
                            {tag.name}
                        </button>
                    {/each}
                    {#if searchQuery.trim() && !hasExactMatch}
                        <button
                            type="button"
                            class="flex w-full items-center gap-1 px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent"
                            onclick={handleCreateFromSearch}
                        >
                            Create "{searchQuery.trim()}"
                        </button>
                    {/if}
                </div>
            {/if}
        </div>
    </div>
</Segment>

<!-- Delete confirmation dialog -->
<Dialog.Root
    open={!!deletingTag}
    onOpenChange={(open: boolean) => {
        if (!open) deletingTag = null;
    }}
>
    <Dialog.Content class="sm:max-w-[360px]">
        <Dialog.Header>
            <Dialog.Title>Delete tag "{deletingTag?.name}"?</Dialog.Title>
            <Dialog.Description>
                This will permanently remove it from {deleteTagSampleCount} sample{deleteTagSampleCount ===
                1
                    ? ''
                    : 's'}.
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Button variant="outline" onclick={() => (deletingTag = null)}>Cancel</Button>
            <Button variant="destructive" onclick={confirmDelete}>Delete</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
