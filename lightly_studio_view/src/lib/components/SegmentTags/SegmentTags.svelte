<script lang="ts">
    /*
     * TAGGING WORKFLOW PROTOTYPE — SegmentTags (detail-view right panel)
     *
     * Codebase findings (explored 2026-04-02):
     * - Sample tags arrive as TagTable[] (tag_id?: string, name: string, kind, collection_id)
     *   via sample.tags from the detail-view loader.
     * - The previous version had a tagId vs tag_id camelCase bug (transform in
     *   SampleDetailsSidePanel produced { tagId, name } but SegmentTags expected { tag_id? }).
     *   Fixed here by accepting TagTable[] directly.
     * - Remove API: onRemoveTag prop → SampleDetailsPanel.handleRemoveTag →
     *     useRemoveTagFromSample hook → removeTagFromSample({ collection_id, sample_id, tag_id })
     * - Assign existing tag API: addSampleIdsToTagId({ path: {collection_id, tag_id}, body: {sample_ids} })
     * - Create + assign API: createTag() then addSampleIdsToTagId()
     * - allCollectionTags from useTags({ collection_id, kind:['sample'] }) in parent.
     */
    import { Segment } from '$lib/components';
    import { TagsIcon, Pencil, Plus, X } from '@lucide/svelte';
    import type { TagView } from '$lib/services/types';
    import {
        createTag,
        addSampleIdsToTagId,
        removeTagFromSample as removeTagFromSampleApi
    } from '$lib/api/lightly_studio_local';
    import { toast } from 'svelte-sonner';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    // Minimal tag shape — broad enough for TagTable, AnnotationViewTag, and simple objects.
    interface TagItem {
        tag_id?: string;
        name: string;
    }

    interface Props {
        tags: TagItem[];
        /** Full collection tag list for autocomplete. When omitted, chip-swap and add-tag are hidden. */
        allCollectionTags?: TagView[];
        tagKind?: TagView['kind'];
        collectionId?: string;
        sampleId?: string;
        onRemoveTag?: (tagId: string) => Promise<void>;
        onClick?: (tagId: string) => Promise<void>;
        onRefetch?: () => void;
    }

    let {
        tags,
        allCollectionTags = [],
        tagKind = 'sample',
        collectionId = '',
        sampleId = '',
        onRemoveTag,
        onClick,
        onRefetch = () => {}
    }: Props = $props();
    const removeTagHandler = onRemoveTag ?? onClick ?? (async () => undefined);

    const { tags: tagsByCollection, adjustTagSampleCount } = useGlobalStorage();

    // Chip-swap and add-tag require collectionId + sampleId to be wired up.
    const canEdit = $derived(!!collectionId && !!sampleId);

    // ── Chip swap state ─────────────────────────────────────────────────────────
    let editingTagId = $state<string | null>(null);
    let editQuery = $state('');
    let showEditDropdown = $state(false);

    // ── Add-tag state ────────────────────────────────────────────────────────────
    let showAddInput = $state(false);
    let addQuery = $state('');
    let showAddDropdown = $state(false);
    let addBusy = $state(false);

    // ── Derived option lists ─────────────────────────────────────────────────────
    const editOptions = $derived(
        allCollectionTags.filter(
            (t) =>
                t.tag_id !== editingTagId &&
                t.name.toLowerCase().includes(editQuery.toLowerCase()) &&
                !tags.some((existing) => existing.tag_id === t.tag_id)
        )
    );

    const addOptions = $derived(
        allCollectionTags.filter(
            (t) =>
                t.name.toLowerCase().includes(addQuery.toLowerCase()) &&
                !tags.some((existing) => existing.tag_id === t.tag_id)
        )
    );

    const hasExactAddMatch = $derived(
        allCollectionTags.some((t) => t.name.toLowerCase() === addQuery.trim().toLowerCase())
    );

    const hasExactEditMatch = $derived(
        allCollectionTags.some((t) => t.name.toLowerCase() === editQuery.trim().toLowerCase())
    );

    // ── Chip-swap handlers ───────────────────────────────────────────────────────
    function startEdit(tag: TagItem) {
        if (!tag.tag_id) return;
        editingTagId = tag.tag_id;
        editQuery = tag.name;
        showEditDropdown = true;
    }

    function cancelEdit() {
        editingTagId = null;
        editQuery = '';
        showEditDropdown = false;
    }

    function addCreatedTagToGlobalStore(tag: TagView) {
        if (!collectionId) return;

        tagsByCollection.update((allTagsByCollection) => {
            const existingTags = allTagsByCollection[collectionId] ?? [];
            if (existingTags.some((existingTag) => existingTag.tag_id === tag.tag_id)) {
                return allTagsByCollection;
            }

            return {
                ...allTagsByCollection,
                [collectionId]: [...existingTags, tag]
            };
        });
    }

    async function applyTagSwap(oldTagId: string, newTag: TagView) {
        if (newTag.tag_id === oldTagId) {
            cancelEdit();
            return;
        }
        // Call API directly to avoid onRemoveTag triggering an intermediate refetch
        const removeResponse = await removeTagFromSampleApi({
            path: { collection_id: collectionId, sample_id: sampleId, tag_id: oldTagId }
        });
        if (removeResponse.error) {
            toast.error('Failed to update tag. Please try again.');
            return;
        }
        const addResponse = await addSampleIdsToTagId({
            path: { collection_id: collectionId, tag_id: newTag.tag_id },
            body: { sample_ids: [sampleId] }
        });
        if (addResponse.error) {
            await addSampleIdsToTagId({
                path: { collection_id: collectionId, tag_id: oldTagId },
                body: { sample_ids: [sampleId] }
            });
            toast.error('Failed to update tag. Please try again.');
            return;
        }
        adjustTagSampleCount(oldTagId, -1);
        adjustTagSampleCount(newTag.tag_id, 1);
        cancelEdit();
        onRefetch();
    }

    async function handleCreateAndSwap(oldTagId: string, name: string) {
        const trimmed = name.trim();
        if (!trimmed) return;

        const currentTag = tags.find((tag) => tag.tag_id === oldTagId);
        if (!currentTag) {
            cancelEdit();
            return;
        }
        if (currentTag.name.toLowerCase() === trimmed.toLowerCase()) {
            cancelEdit();
            return;
        }

        const response = await createTag({
            path: { collection_id: collectionId },
            body: { name: trimmed, description: `${trimmed} description`, kind: tagKind }
        });
        if (response.error || !response.data) {
            toast.error('Failed to update tag. Please try again.');
            return;
        }

        addCreatedTagToGlobalStore(response.data);

        await applyTagSwap(oldTagId, response.data);
    }

    // ── Add-tag handlers ─────────────────────────────────────────────────────────
    function openAddInput() {
        showAddInput = true;
        addQuery = '';
        showAddDropdown = false;
    }

    function closeAddInput() {
        showAddInput = false;
        addQuery = '';
        showAddDropdown = false;
    }

    async function handleAddExisting(tag: TagView) {
        addBusy = true;
        try {
            const response = await addSampleIdsToTagId({
                path: { collection_id: collectionId, tag_id: tag.tag_id },
                body: { sample_ids: [sampleId] }
            });
            if (response.error) {
                throw new Error('assign tag failed');
            }
            adjustTagSampleCount(tag.tag_id, 1);
        } catch {
            toast.error('Failed to add tag. Please try again.');
            return;
        } finally {
            addBusy = false;
        }
        closeAddInput();
        onRefetch();
    }

    async function handleCreateAndAdd(name: string) {
        const trimmed = name.trim();
        if (!trimmed) return;
        addBusy = true;
        try {
            const response = await createTag({
                path: { collection_id: collectionId },
                body: { name: trimmed, description: `${trimmed} description`, kind: tagKind }
            });
            if (response.error) {
                throw new Error('create tag failed');
            }
            if (response.data?.tag_id) {
                addCreatedTagToGlobalStore(response.data);
                const addResponse = await addSampleIdsToTagId({
                    path: { collection_id: collectionId, tag_id: response.data.tag_id },
                    body: { sample_ids: [sampleId] }
                });
                if (addResponse.error) {
                    throw new Error('assign tag failed');
                }
                adjustTagSampleCount(response.data.tag_id, 1);
            }
        } catch {
            toast.error('Failed to add tag. Please try again.');
            return;
        } finally {
            addBusy = false;
        }
        closeAddInput();
        onRefetch();
    }

    function handleEditKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') cancelEdit();
        if (event.key === 'Enter' && editingTagId && editQuery.trim() && !hasExactEditMatch) {
            void handleCreateAndSwap(editingTagId, editQuery);
        }
    }

    function handleAddKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') closeAddInput();
        if (event.key === 'Enter' && addQuery.trim() && !hasExactAddMatch) {
            handleCreateAndAdd(addQuery);
        }
    }

    async function handleRemoveExisting(tagId: string) {
        await removeTagHandler(tagId);
        adjustTagSampleCount(tagId, -1);
    }
</script>

<Segment title="Tags" icon={TagsIcon}>
    <div class="flex flex-wrap gap-1">
        {#each tags as tag (tag.tag_id)}
            {#if editingTagId === tag.tag_id}
                <!-- Inline combobox for tag reassignment -->
                <div class="relative">
                    <div
                        class="flex items-center gap-1 rounded-lg border border-primary bg-card px-2 py-1 text-xs"
                    >
                        <!-- svelte-ignore a11y_autofocus -->
                        <input
                            type="text"
                            bind:value={editQuery}
                            class="w-24 bg-transparent outline-none"
                            autofocus
                            oninput={() => (showEditDropdown = true)}
                            onkeydown={handleEditKeydown}
                        />
                        <button
                            type="button"
                            onclick={cancelEdit}
                            class="text-muted-foreground hover:text-foreground"
                            aria-label="Cancel edit"
                        >
                            <X class="size-3" />
                        </button>
                    </div>
                    {#if showEditDropdown && editOptions.length > 0}
                        <div
                            class="absolute left-0 top-full z-50 mt-1 max-h-40 w-40 overflow-auto rounded-md border bg-popover shadow-md"
                        >
                            {#each editOptions as opt (opt.tag_id)}
                                <button
                                    type="button"
                                    class="flex w-full items-center px-2 py-1.5 text-xs hover:bg-accent"
                                    onclick={() => tag.tag_id && applyTagSwap(tag.tag_id, opt)}
                                >
                                    {opt.name}
                                </button>
                            {/each}
                            {#if editQuery.trim() && !hasExactEditMatch && tag.tag_id}
                                <button
                                    type="button"
                                    class="flex w-full items-center px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent"
                                    onclick={() => handleCreateAndSwap(tag.tag_id!, editQuery)}
                                >
                                    Create "{editQuery.trim()}"
                                </button>
                            {/if}
                        </div>
                    {:else if showEditDropdown && editQuery.trim() && !hasExactEditMatch && tag.tag_id}
                        <div
                            class="absolute left-0 top-full z-50 mt-1 max-h-40 w-40 overflow-auto rounded-md border bg-popover shadow-md"
                        >
                            <button
                                type="button"
                                class="flex w-full items-center px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent"
                                onclick={() => handleCreateAndSwap(tag.tag_id!, editQuery)}
                            >
                                Create "{editQuery.trim()}"
                            </button>
                        </div>
                    {/if}
                </div>
            {:else}
                <div class="group inline-flex items-center gap-1 rounded-lg bg-card px-2 py-1 text-xs">
                    {#if canEdit}
                        <button
                            type="button"
                            class="text-muted-foreground opacity-0 transition group-hover:opacity-100 hover:text-foreground"
                            aria-label={`Reassign tag ${tag.name}`}
                            onclick={() => startEdit(tag)}
                        >
                            <Pencil class="size-3" />
                        </button>
                    {/if}
                    <span data-testid="segment-tag-name">{tag.name}</span>
                    <button
                        type="button"
                        class="flex size-4 items-center justify-center rounded-full text-muted-foreground transition hover:text-destructive focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                        aria-label={`Remove tag ${tag.name}`}
                        data-testid={`remove-tag-${tag.name}`}
                        onclick={(event) => {
                            event.stopPropagation();
                            if (tag.tag_id) void handleRemoveExisting(tag.tag_id);
                        }}
                    >
                        x
                    </button>
                </div>
            {/if}
        {/each}
    </div>

    <!-- Add-tag control -->
    <div class="relative mt-2">
        {#if showAddInput}
            <div
                class="flex items-center gap-1 rounded-lg border border-primary bg-card px-2 py-1 text-xs"
            >
                <Plus class="size-3 shrink-0 text-muted-foreground" />
                <!-- svelte-ignore a11y_autofocus -->
                <input
                    type="text"
                    bind:value={addQuery}
                    placeholder="Tag name..."
                    class="min-w-0 flex-1 bg-transparent outline-none"
                    autofocus
                    disabled={addBusy}
                    oninput={() => (showAddDropdown = true)}
                    onkeydown={handleAddKeydown}
                />
                <button
                    type="button"
                    onclick={closeAddInput}
                    class="shrink-0 text-muted-foreground hover:text-foreground"
                    aria-label="Cancel"
                >
                    <X class="size-3" />
                </button>
            </div>
            {#if showAddDropdown && (addOptions.length > 0 || (addQuery.trim() && !hasExactAddMatch))}
                <div
                    class="absolute left-0 top-full z-50 mt-1 max-h-40 w-full overflow-auto rounded-md border bg-popover shadow-md"
                >
                    {#each addOptions as opt (opt.tag_id)}
                        <button
                            type="button"
                            class="flex w-full items-center px-2 py-1.5 text-xs hover:bg-accent"
                            onclick={() => handleAddExisting(opt)}
                        >
                            {opt.name}
                        </button>
                    {/each}
                    {#if addQuery.trim() && !hasExactAddMatch}
                        <button
                            type="button"
                            class="flex w-full items-center px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent"
                            onclick={() => handleCreateAndAdd(addQuery)}
                        >
                            Create "{addQuery.trim()}"
                        </button>
                    {/if}
                </div>
            {/if}
        {:else}
            <button
                type="button"
                class="flex items-center gap-1 rounded px-1 py-0.5 text-xs text-muted-foreground transition hover:text-foreground"
                onclick={openAddInput}
            >
                <Plus class="size-3" />
                Add tag
            </button>
        {/if}
    </div>
</Segment>
