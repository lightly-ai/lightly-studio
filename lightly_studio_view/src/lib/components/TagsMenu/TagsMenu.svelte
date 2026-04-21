<script lang="ts">
    import { tick } from 'svelte';
    import { Checkbox } from '$lib/components';
    import type { GridType } from '$lib/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox as CheckboxPrimitive } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import * as Popover from '$lib/components/ui/popover';
    import { Check, MoreHorizontal, Pencil, Tags as Tagsicon, Trash2 } from '@lucide/svelte';
    import type { TagView } from '$lib/services/types';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        createTag,
        addSampleIdsToTagId,
        deleteTag,
        updateTag
    } from '$lib/api/lightly_studio_local';
    import TagAssignInput from './TagAssignInput.svelte';
    import { toast } from 'svelte-sonner';

    let { collection_id, gridType }: Parameters<typeof useTags>[0] & { gridType: GridType } =
        $props();

    const tagKind = $derived(gridType === 'annotations' ? 'annotation' : 'sample');

    const { tags, tagsSelected, tagSelectionToggle, loadTags, clearTagSelected } = $derived(
        useTags({ collection_id, kind: [tagKind] })
    );

    const { getSelectedSampleIds, selectedSampleAnnotationCropIds } = useGlobalStorage();

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

    // ── Selection assignment ─────────────────────────────────────────────────────
    let assignBusy = $state(false);
    let deletingTagId = $state<string | null>(null);
    let editingTagId = $state<string | null>(null);
    let renamingTagId = $state<string | null>(null);
    let openActionsTagId = $state<string | null>(null);
    let suppressCloseAutoFocusTagId = $state<string | null>(null);
    let renameValue = $state('');
    let renameInputRef = $state<HTMLInputElement | null>(null);

    const editedTag = $derived($tags.find((tag: TagView) => tag.tag_id === editingTagId) ?? null);
    const trimmedRenameValue = $derived(renameValue.trim());
    const renameSaveDisabled = $derived(
        !editedTag ||
            renamingTagId !== null ||
            trimmedRenameValue.length === 0 ||
            trimmedRenameValue === editedTag.name
    );

    async function handleAssign(name: string) {
        assignBusy = true;
        try {
            const existingTag = $tags.find(
                (t: TagView) => t.name.toLowerCase() === name.toLowerCase()
            );
            if (existingTag) {
                const response = await addSampleIdsToTagId({
                    path: { collection_id, tag_id: existingTag.tag_id },
                    body: { sample_ids: [...selectedIds] }
                });
                if (response.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
            } else {
                const createResponse = await createTag({
                    path: { collection_id },
                    body: { name, description: `${name} description`, kind: tagKind }
                });
                if (createResponse.error || !createResponse.data?.tag_id) {
                    toast.error('Failed to create tag. Please try again.');
                    return;
                }
                const assignResponse = await addSampleIdsToTagId({
                    path: { collection_id, tag_id: createResponse.data.tag_id },
                    body: { sample_ids: [...selectedIds] }
                });
                if (assignResponse.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
            }
            loadTags();
        } catch (error) {
            console.error('Failed to assign tag', error);
            toast.error('Failed to assign tag. Please try again.');
        } finally {
            assignBusy = false;
        }
    }

    async function handleDeleteTag(tag: TagView, event: MouseEvent) {
        event.stopPropagation();

        if (deletingTagId) {
            return;
        }

        deletingTagId = tag.tag_id;

        try {
            const response = await deleteTag({
                path: {
                    collection_id,
                    tag_id: tag.tag_id
                }
            });

            if (response.error) {
                throw new Error('Failed to delete tag.');
            }

            clearTagSelected(tag.tag_id);
            loadTags();
            toast.success('Tag deleted successfully');
        } catch {
            toast.error('Failed to delete tag. Please try again.');
        } finally {
            deletingTagId = null;
        }
    }

    async function openRename(tag: TagView, event: MouseEvent) {
        event.stopPropagation();
        if (deletingTagId || renamingTagId) {
            return;
        }
        suppressCloseAutoFocusTagId = tag.tag_id;
        openActionsTagId = null;
        editingTagId = tag.tag_id;
        renameValue = tag.name;
        await tick();
        renameInputRef?.focus();
        renameInputRef?.select();
    }

    function cancelRename(event?: MouseEvent) {
        event?.stopPropagation();
        editingTagId = null;
        renameValue = '';
    }

    async function handleRename(tag: TagView, event: MouseEvent | KeyboardEvent) {
        event.stopPropagation();

        const name = renameValue.trim();
        if (renamingTagId || name.length === 0 || name === tag.name) {
            return;
        }

        renamingTagId = tag.tag_id;

        try {
            const response = await updateTag({
                path: {
                    collection_id,
                    tag_id: tag.tag_id
                },
                body: {
                    name,
                    description: tag.description,
                    kind: tag.kind
                }
            });

            if (response.error) {
                throw new Error('Failed to rename tag.');
            }

            cancelRename();
            loadTags();
        } catch {
            toast.error('Failed to rename tag. Please try again.');
        } finally {
            renamingTagId = null;
        }
    }
</script>

<Segment title="Tags" icon={Tagsicon}>
    <div class="mb-3 w-full space-y-1">
        <div class="space-y-1">
            {#each $tags as tag (tag.tag_id)}
                <div class="flex items-center gap-2 py-0.5" data-testid="tag-menu-item">
                    <div class="min-w-0 flex-1">
                        {#if editingTagId === tag.tag_id}
                            <div
                                class="flex items-center gap-2"
                                data-testid={`rename-tag-form-${tag.tag_id}`}
                            >
                                <CheckboxPrimitive
                                    checked={$tagsSelected.has(tag.tag_id)}
                                    onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                                    disabled={renamingTagId === tag.tag_id}
                                />
                                <Input
                                    bind:ref={renameInputRef}
                                    bind:value={renameValue}
                                    autofocus
                                    class="h-8 text-xs"
                                    data-testid={`rename-tag-input-${tag.tag_id}`}
                                    placeholder="Tag name"
                                    disabled={renamingTagId === tag.tag_id}
                                    onclick={(event: MouseEvent) => {
                                        event.stopPropagation();
                                    }}
                                    onkeydown={(event: KeyboardEvent) => {
                                        event.stopPropagation();
                                        if (event.key === 'Enter') {
                                            event.preventDefault();
                                            void handleRename(tag, event);
                                        }
                                        if (event.key === 'Escape') {
                                            event.preventDefault();
                                            cancelRename();
                                        }
                                    }}
                                />
                                <button
                                    type="button"
                                    class="inline-flex size-7 shrink-0 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
                                    data-testid={`save-tag-rename-${tag.tag_id}`}
                                    disabled={renameSaveDisabled}
                                    onclick={(event: MouseEvent) => {
                                        void handleRename(tag, event);
                                    }}
                                >
                                    <Check class="size-4" />
                                </button>
                            </div>
                        {:else}
                            <Checkbox
                                name={tag.tag_id}
                                isChecked={$tagsSelected.has(tag.tag_id)}
                                label={tag.name}
                                onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                            />
                        {/if}
                    </div>
                    <Popover.Root
                        open={openActionsTagId === tag.tag_id}
                        onOpenChange={(open) => {
                            openActionsTagId = open ? tag.tag_id : null;
                        }}
                    >
                        <Popover.Trigger
                            class="inline-flex size-7 shrink-0 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
                            aria-label={`Open actions for tag ${tag.name}`}
                            data-testid={`tag-actions-trigger-${tag.tag_id}`}
                            disabled={deletingTagId === tag.tag_id || renamingTagId === tag.tag_id}
                            onclick={(event: MouseEvent) => {
                                event.stopPropagation();
                            }}
                        >
                            <MoreHorizontal />
                        </Popover.Trigger>
                        <Popover.Content
                            class="w-40 p-1"
                            align="end"
                            onCloseAutoFocus={(event) => {
                                if (suppressCloseAutoFocusTagId === tag.tag_id) {
                                    event.preventDefault();
                                    suppressCloseAutoFocusTagId = null;
                                }
                            }}
                            onclick={(event: MouseEvent) => {
                                event.stopPropagation();
                            }}
                        >
                            <button
                                type="button"
                                class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                data-testid={`rename-tag-${tag.tag_id}`}
                                disabled={deletingTagId !== null || renamingTagId !== null}
                                onclick={(event: MouseEvent) => {
                                    openRename(tag, event);
                                }}
                            >
                                <Pencil class="size-4" />
                                Rename tag
                            </button>
                            <button
                                type="button"
                                class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-foreground transition-colors hover:bg-destructive hover:text-destructive-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                data-testid={`delete-tag-${tag.tag_id}`}
                                disabled={deletingTagId !== null || renamingTagId !== null}
                                onclick={(event: MouseEvent) => {
                                    void handleDeleteTag(tag, event);
                                }}
                            >
                                <Trash2 class="size-4" />
                                {deletingTagId === tag.tag_id ? 'Deleting...' : 'Delete tag'}
                            </button>
                        </Popover.Content>
                    </Popover.Root>
                </div>
            {:else}
                <p>No tags yet</p>
            {/each}
        </div>

        <TagAssignInput
            options={$tags}
            busy={assignBusy || !hasSelection}
            onSelect={handleAssign}
        />
    </div>
</Segment>
