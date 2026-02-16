<script lang="ts">
    import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import {
        createTag,
        addSampleIdsToTagId,
        readImages,
        type ReadImagesRequest,
        getAllFrames,
        type VideoFrameFilter,
        getAllVideos,
        readAnnotationsWithPayload,
        type SampleFilter
    } from '$lib/api/lightly_studio_local';
    import type { TagKind } from '$lib/services/types';
    import type { GridType } from '$lib/types';
    import { cn } from '$lib/utils';
    import { createMutation } from '@tanstack/svelte-query';
    import { SvelteSet } from 'svelte/reactivity';

    import { Checkbox } from '$lib/components';
    import { Alert } from '$lib/components/index.js';
    import { Input } from '$lib/components/ui/input';
    import { useGlobalStorage, type TextEmbedding } from '$lib/hooks/useGlobalStorage';
    import { useTags } from '$lib/hooks/useTags/useTags.js';

    import { Eraser as EraserIcon, Plus as AddIcon } from '@lucide/svelte';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import Spinner from '../Spinner/Spinner.svelte';
    import type { Writable } from 'svelte/store';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { isNormalModeParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';

    export type UseTagsCreateDialog = {
        collectionId: string;
        gridType: GridType;
        selectedAnnotationFilterIds?: Writable<Set<string>>;
        textEmbedding?: TextEmbedding;
    };

    let {
        collectionId,
        gridType,
        selectedAnnotationFilterIds,
        textEmbedding
    }: UseTagsCreateDialog = $props();

    const { metadataValues } = useMetadataFilters(collectionId);
    let tagKind: TagKind = $derived(
        ['samples', 'videos', 'video_frames'].includes(gridType) ? 'sample' : 'annotation'
    );
    const { tags, loadTags, tagsSelected } = $derived(
        useTags({ collection_id: collectionId, kind: [tagKind] })
    );
    const { dimensionsValues: dimensions } = useDimensions();
    const { filterParams } = useImageFilters();
    const { filterParams: videoFilterParams } = useVideoFilters();

    const sampleFilter = $derived<SampleFilter>({
        annotation_label_ids: $selectedAnnotationFilterIds?.size
            ? Array.from($selectedAnnotationFilterIds)
            : [],
        tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
        metadata_filters: $metadataValues ? createMetadataFilters($metadataValues) : undefined
    });
    const imageParams = $derived<ReadImagesRequest>({
        filters: {
            sample_filter: {
                sample_ids: isNormalModeParams($filterParams)
                    ? $filterParams.filters?.sample_ids
                    : undefined,
                ...sampleFilter
            },
            ...$dimensions
        },
        text_embedding: textEmbedding?.embedding
    });

    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const videoFramesFilter = $derived<VideoFrameFilter>({
        sample_filter: sampleFilter,
        ...$videoFramesBoundsValues
    });

    const { videoBoundsValues } = useVideoBounds();

    const videosFilter = $derived<VideoFrameFilter>({
        sample_filter: {
            sample_ids: $videoFilterParams?.filters?.sample_ids,
            ...sampleFilter
        },
        ...$videoBoundsValues
    });

    const annotationsQueryParams = $derived({
        annotation_label_ids: $selectedAnnotationFilterIds?.size
            ? Array.from($selectedAnnotationFilterIds)
            : undefined,
        tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined
    });

    // setup global selection state
    const {
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,
        clearSelectedSampleAnnotationCrops,
        clearSelectedSamples
    } = useGlobalStorage();
    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));
    const clearItemsSelected = $derived(
        ['samples', 'videos', 'video_frames'].includes(gridType)
            ? () => clearSelectedSamples(collectionId)
            : () => clearSelectedSampleAnnotationCrops(collectionId)
    );

    let itemsSelectedByFilter = $state<Set<string> | null>(null);
    const itemsSelected = $derived.by(() => {
        if (itemsSelectedByFilter?.size) return itemsSelectedByFilter;

        return ['samples', 'videos', 'video_frames'].includes(gridType)
            ? $selectedSampleIds
            : $selectedSampleAnnotationCropIds[collectionId];
    });

    const sampleText = $derived.by(() => {
        if (tagKind == 'sample') {
            return itemsSelected.size > 1 ? 'samples' : 'sample';
        }

        if (tagKind == 'annotation') {
            return itemsSelected.size > 1 ? 'annotations' : 'annotation';
        }
    });
    // setup initial dialog state
    let isDialogOpened = $state(false);
    const isDialogOpenable = $derived(
        ($selectedSampleIds.size > 0 && ['samples', 'videos', 'video_frames'].includes(gridType)) ||
            ($selectedSampleAnnotationCropIds[collectionId]?.size > 0 && gridType === 'annotations')
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
                        collection_id: collectionId
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
                const response = await addSampleIdsToTagId({
                    path: {
                        collection_id: collectionId,
                        tag_id: tagId
                    },
                    body: {
                        sample_ids: [...itemsSelected]
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
        hasFetched = false;
        tagsEnlistedToCreate = [];
        tagsToAddItemsTo.clear();
        itemsSelectedByFilter = null;
    };

    const changesToCommit = $derived(tagsToAddItemsTo.size > 0 || tagsEnlistedToCreate.length > 0);

    let isCreateByFilter = $state(false);
    let hasFetched = false;

    const fetchSamples = async () => {
        if (!isCreateByFilter || hasFetched) return;
        hasFetched = true;
        if (gridType == 'samples') {
            const images = await readImages({
                path: {
                    collection_id: collectionId
                },
                body: {
                    ...imageParams
                }
            });

            const sampleIds = images.data?.data?.map((e) => e.sample_id);

            itemsSelectedByFilter = new Set(sampleIds);
        } else if (gridType == 'video_frames') {
            const videoFrames = await getAllFrames({
                path: {
                    video_frame_collection_id: collectionId
                },
                body: {
                    filter: videoFramesFilter
                }
            });

            const sampleIds = videoFrames.data?.data?.map((e) => e.sample_id);

            itemsSelectedByFilter = new Set(sampleIds);
        } else if (gridType == 'videos') {
            const videos = await getAllVideos({
                path: {
                    collection_id: collectionId
                },
                body: {
                    filter: videosFilter
                }
            });

            const sampleIds = videos.data?.data?.map((e) => e.sample_id);

            itemsSelectedByFilter = new Set(sampleIds);
        } else if (gridType == 'annotations') {
            const annotations = await readAnnotationsWithPayload({
                path: {
                    collection_id: collectionId
                },
                query: annotationsQueryParams
            });

            const sampleIds = annotations.data?.data?.map((e) => e.annotation.sample_id);

            itemsSelectedByFilter = new Set(sampleIds);
        }
    };
</script>

<div class="flex space-x-1">
    <Button
        variant="outline"
        class={'flex-1'}
        onclick={() => {
            isDialogOpened = true;
            isCreateByFilter = !isDialogOpenable;
        }}
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
        {#await fetchSamples()}
            <Spinner />
        {:then}
            <Dialog.Header>
                <Dialog.Title>Add the selected {sampleText} to a tag</Dialog.Title>
                <Dialog.Description>
                    Add the selected {itemsSelected.size}
                    {sampleText} to an new or existing tag. Tags can later be exported.
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
        {/await}
    </Dialog.Content>
</Dialog.Root>
