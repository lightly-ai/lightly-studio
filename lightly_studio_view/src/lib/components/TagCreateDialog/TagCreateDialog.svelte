<script lang="ts">
    import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import {
        createTag,
        addSampleIdsToTagId,
        addAnnotationIdsToTagId
    } from '$lib/api/lightly_studio_local';
    import type { TagKind } from '$lib/services/types';
    import type { GridType } from '$lib/types';
    import { cn } from '$lib/utils';
    import { createMutation } from '@tanstack/svelte-query';
    import { SvelteSet } from 'svelte/reactivity';

    import { Checkbox } from '$lib/components';
    import { Alert } from '$lib/components/index.js';
    import { Input } from '$lib/components/ui/input';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useTags } from '$lib/hooks/useTags/useTags.js';

    import EraserIcon from '@lucide/svelte/icons/eraser';
    import AddIcon from '@lucide/svelte/icons/plus';

    export type UseTagsCreateDialog = {
        datasetId: string;
        gridType: GridType;
    };

    let { datasetId, gridType }: UseTagsCreateDialog = $props();
    let tagKind: TagKind = $derived(
        ['samples', 'videos', 'video_frames'].includes(gridType) ? 'sample' : 'annotation'
    );
    const { tags, loadTags } = $derived(useTags({ dataset_id: datasetId, kind: [tagKind] }));

    // setup global selection state
    const {
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,
        clearSelectedSampleAnnotationCrops,
        clearSelectedSamples
    } = useGlobalStorage();
    const selectedSampleIds = getSelectedSampleIds(datasetId);
    const clearItemsSelected = $derived(
        ['samples', 'videos', 'video_frames'].includes(gridType)
            ? () => clearSelectedSamples(datasetId)
            : () => clearSelectedSampleAnnotationCrops(datasetId)
    );
    const itemsSelected = $derived(
        ['samples', 'videos', 'video_frames'].includes(gridType)
            ? $selectedSampleIds
            : $selectedSampleAnnotationCropIds[datasetId]
    );

    // setup initial dialog state
    let isDialogOpened = $state(false);
    const isDialogOpenable = $derived(
        ($selectedSampleIds.size > 0 && ['samples', 'videos', 'video_frames'].includes(gridType)) ||
            ($selectedSampleAnnotationCropIds[datasetId]?.size > 0 && gridType === 'annotations')
    );

    // tag creation
    let tagsQueryTerm = $state<string>('');
    let tagsEnlistedToCreate = $state<string[]>([]);
    let onEnlisttagsEnlistedToCreate = () => {
        tagsEnlistedToCreate.push(tagsQueryTerm);
        tagsToAddItemsTo.add(tagsQueryTerm);
        tagsQueryTerm = '';
    };

    // filter tags and tagsEnlistedToCreate based on query term
    const tagsFiltered = $derived.by(() => {
        return [
            // create "fake" tags for the ones we will create
            ...tagsEnlistedToCreate.map((name) => {
                return {
                    tag_id: name,
                    name: name,
                    kind: tagKind
                };
            }),
            // filter "real tags"
            ...$tags
        ].filter((tag) => tag.name.includes(tagsQueryTerm));
    });

    // tag assignment
    let tagsToAddItemsTo = $state(new SvelteSet<string>());
    const tagSelectionToggle = (tag_id: string) => {
        if (tagsToAddItemsTo.has(tag_id)) {
            tagsToAddItemsTo.delete(tag_id);

            // if the tag was added to the list of tags to create, remove it
            tagsEnlistedToCreate.splice(tagsEnlistedToCreate.indexOf(tag_id), 1);
        } else {
            tagsToAddItemsTo.add(tag_id);
        }
    };

    let error = $state<Error | null>(null);

    const submitTagAssignment = async () => {
        // create each tag created by the user
        await Promise.all(
            [...tagsEnlistedToCreate].map(async (tag_name) => {
                // create tag
                const response = await createTag({
                    path: {
                        dataset_id: datasetId
                    },
                    body: {
                        name: tag_name,
                        description: `${tag_name} description`,
                        kind: tagKind
                    }
                });
                if (response.error) {
                    throw new Error(JSON.stringify(response.error));
                }

                // replace the tag name with the tag id
                if (response.data?.tag_id) {
                    tagsToAddItemsTo.delete(tag_name);
                    tagsToAddItemsTo.add(response.data.tag_id);
                }

                return response;
            })
        );

        // assign tags to the selected items
        await Promise.all(
            [...tagsToAddItemsTo].map(async (tagId) => {
                const response =
                    tagKind === 'sample'
                        ? await addSampleIdsToTagId({
                              path: {
                                  dataset_id: datasetId,
                                  tag_id: tagId
                              },
                              body: {
                                  sample_ids: [...itemsSelected]
                              }
                          })
                        : await addAnnotationIdsToTagId({
                              path: {
                                  dataset_id: datasetId,
                                  tag_id: tagId
                              },
                              body: {
                                  annotation_ids: [...itemsSelected]
                              }
                          });

                if (response.error) {
                    throw new Error(JSON.stringify(response.error));
                }
                return response;
            })
        );
    };

    const submitTagAndMutate = createMutation({
        mutationFn: async () => {
            await submitTagAssignment();
        },
        onError: (mutationError: Error) => {
            error = mutationError;
        },
        onSuccess: () => {
            // make other components aware of the change and reload
            loadTags();

            // reset the selected items
            clearItemsSelected();

            // close dialog and reset state
            changeDialogOpenState(false);
            // TODO: add toast/notification
        }
    });

    const changeDialogOpenState = (newDialogState: boolean) => {
        isDialogOpened = newDialogState;

        // reset state when unmounting
        error = null;
        tagsQueryTerm = '';
        tagsEnlistedToCreate = [];
        tagsToAddItemsTo.clear();
    };

    const changesToCommit = $derived(tagsToAddItemsTo.size > 0 || tagsEnlistedToCreate.length > 0);
</script>

<div class="flex space-x-1">
    <Button
        variant="outline"
        disabled={!isDialogOpenable}
        class={'flex-1'}
        onclick={() => (isDialogOpened = true)}
        data-testid="tag-create-dialog-button"
    >
        <AddIcon />
        Create new Tags
    </Button>
    <Button
        variant="outline"
        disabled={!isDialogOpenable}
        size="icon"
        title="Clear selection"
        onclick={clearItemsSelected}
    >
        <EraserIcon />
    </Button>
</div>
<Dialog.Root onOpenChange={changeDialogOpenState} open={isDialogOpened}>
    <Dialog.Content class="sm:max-w-[425px]">
        <Dialog.Header>
            <Dialog.Title>Add the selected {tagKind} to a tag</Dialog.Title>
            <Dialog.Description>
                Add the selected {itemsSelected.size}
                {tagKind} to an new or existing tag. Tags can later be exported.
            </Dialog.Description>
        </Dialog.Header>
        {#if error}
            <Alert title="Error occured">{error}</Alert>
        {/if}
        <div class="grid gap-4">
            <Input
                type="text"
                placeholder="Create or search tags"
                bind:value={tagsQueryTerm}
                autofocus
                data-testid="tag-create-dialog-input"
            />
        </div>
        <div>
            {#each tagsFiltered as tag (tag.tag_id)}
                <div class="flex space-x-2 py-1">
                    <Checkbox
                        name={`tagCreateDialog-tag-${tag.tag_id}`}
                        isChecked={tagsToAddItemsTo.has(tag.tag_id)}
                        label={tag.name}
                        onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                    />
                </div>
            {/each}
            {#if tagsQueryTerm}
                <Button
                    type="button"
                    variant="outline"
                    class={cn('', ...buttonVariants({ variant: 'outline' }))}
                    onclick={onEnlisttagsEnlistedToCreate}
                    data-testid="tag-create-dialog-create">Create tag "{tagsQueryTerm}"</Button
                >
            {/if}
        </div>
        <Dialog.Footer>
            {#if changesToCommit}
                <Button
                    type="submit"
                    onclick={() => $submitTagAndMutate.mutate()}
                    data-testid="tag-create-dialog-save">Save changes</Button
                >
            {/if}
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
