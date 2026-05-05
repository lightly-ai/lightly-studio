<script lang="ts">
    import { page } from '$app/state';
    import FormField from '$lib/components/FormField/FormField.svelte';
    import { Checkbox } from '$lib/components';
    import { Button } from '$lib/components/ui';
    import * as Select from '$lib/components/ui/select/index.js';
    import * as Tabs from '$lib/components/ui/tabs/index.js';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { exportCollection } from '$lib/services/exportCollection';
    import type { ExportFilter } from '$lib/services/types';
    import { useExportSamplesCount } from './useExportSamplesCount/useExportSamplesCount';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Loader2 } from '@lucide/svelte';
    import * as Alert from '$lib/components/ui/alert/index.js';
    import { fade } from 'svelte/transition';
    import { useExportDialog } from '$lib/hooks/useExportDialog/useExportDialog';

    const { isExportDialogOpen, openExportDialog, closeExportDialog } = useExportDialog();

    $effect(() => {
        if ($isExportDialogOpen) {
            exportType = isVideoCollection ? 'youtube_vis_segmentation' : 'samples';
        }
    });

    const isVideoCollection = $derived(
        page.data.collection?.sample_type === 'video' ||
            page.data.collection?.sample_type === 'video_frame'
    );

    let exportType = $state<
        | 'samples'
        | 'object_detections'
        | 'segmentation'
        | 'captions'
        | 'youtube_vis_segmentation'
        | 'semantic_segmentations'
    >('samples');
    const exportTypeLabels: Record<typeof exportType, string> = {
        samples: 'Image Filenames',
        object_detections: 'Image Object Detections',
        segmentation: 'Image Segmentation Mask (COCO)',
        semantic_segmentations: 'Image Segmentation Mask (PASCAL VOC)',
        captions: 'Image Captions',
        youtube_vis_segmentation: 'YouTube-VIS Video Segmentation Masks'
    };
    const exportTypeTriggerContent = $derived(exportTypeLabels[exportType]);
    let collectionId = page.params.collection_id;

    //
    // Sample export
    //

    let isSelectionInverted = $state(false);
    let tagIdToExport = $state('');
    const { tags } = useTags({ collection_id: collectionId });

    const triggerContent = $derived(
        $tags.find((f) => f.tag_id === tagIdToExport)?.name ??
            'Select a tag to export its samples (required)'
    );

    // Enable info panel if there are selected samples or annotations or tag is selected
    const isInfoEnabled = $derived(exportType === 'samples' ? tagIdToExport : false);

    const filter = $derived.by(() => {
        const filter: ExportFilter = {};
        // Only "Samples" export mode supports filtering by selected samples.
        if (exportType === 'samples' && tagIdToExport) {
            filter.tag_ids = [tagIdToExport];
        }
        return filter;
    });

    const includeFilter = $derived(isSelectionInverted ? undefined : filter);
    const excludeFilter = $derived(isSelectionInverted ? filter : undefined);

    const {
        count,
        isLoading,
        error: statError
    } = $derived(
        useExportSamplesCount({
            collection_id: collectionId,
            includeFilter,
            excludeFilter
        })
    );

    let errorMessage = $derived.by(() => {
        return $statError ? $statError : '';
    });

    // Disable submit button if no tags are available for samples tab or no tag is selected
    const isSubmitDisabled = $derived.by(() => {
        if (exportType === 'samples') {
            if ($tags.length === 0 || !tagIdToExport) {
                return true;
            }
        }
        return !!errorMessage;
    });

    const handleExport = async () => {
        const response = await exportCollection({
            collection_id: collectionId,
            includeFilter,
            excludeFilter
        });
        if (response.error) {
            errorMessage = `Export failed: ${response.error}`;
        }
    };

    //
    // Annotation export
    //
    const exportAnnotationsURL = `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/annotations?ts=${Date.now()}&export_format=object_detection_coco`;

    //
    // Segmentation mask export
    //
    const exportSegmentationMaskURL = `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/annotations?ts=${Date.now()}&export_format=segmentation_mask_coco`;

    //
    // YouTube-VIS video Segmentation mask export
    //
    const exportYoutubeVisSegmentationMaskURL = `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/youtube-vis?ts=${Date.now()}&export_format=youtube_vis_segmentation`;
    // Semantic segmentation export
    //
    const exportPascalVocURL = `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/annotations?ts=${Date.now()}&export_format=pascal_voc`;

    //
    // Caption export
    //
    const exportCaptionsURL = `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/captions?ts=${Date.now()}`;
</script>

<Dialog.Root
    open={$isExportDialogOpen}
    onOpenChange={(open) => (open ? openExportDialog() : closeExportDialog())}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="flex max-h-[75vh] flex-col border-border bg-background sm:max-w-[550px]"
        >
            <Dialog.Header>
                <Dialog.Title class="text-foreground">Collection Export</Dialog.Title>
            </Dialog.Header>
            <Dialog.Description class="text-muted-foreground">
                Choose the export type:
            </Dialog.Description>

            <div class="grid flex-1 gap-4 overflow-y-auto px-1">
                <Tabs.Root bind:value={exportType} class="w-full">
                    <!-- TODO(lukas 3/2026): Consider constructing this by iterating over exportTypeLabels-->
                    <FormField label="Export Type">
                        <Select.Root type="single" bind:value={exportType}>
                            <Select.Trigger class="w-full" data-testid="export-type-select">
                                {exportTypeTriggerContent}
                            </Select.Trigger>
                            <Select.Content>
                                {#if isVideoCollection}
                                    <Select.Item
                                        value="youtube_vis_segmentation"
                                        label="YouTube-VIS Video Segmentation Masks"
                                        >YouTube-VIS Video Segmentation Masks</Select.Item
                                    >
                                {:else}
                                    <Select.Item value="samples" label="Image Filenames"
                                        >Image Filenames</Select.Item
                                    >
                                    <Select.Item
                                        value="object_detections"
                                        label="Image Object Detections"
                                        >Image Object Detections</Select.Item
                                    >
                                    <Select.Item
                                        value="segmentation"
                                        label="Image Segmentation Mask (COCO)"
                                        >Image Segmentation Mask (COCO)</Select.Item
                                    >
                                    <Select.Item
                                        value="semantic_segmentations"
                                        label="Image Segmentation Mask (PASCAL VOC)"
                                        >Image Segmentation Mask (PASCAL VOC)</Select.Item
                                    >
                                    <Select.Item value="captions" label="Image Captions"
                                        >Image Captions</Select.Item
                                    >
                                {/if}
                            </Select.Content>
                        </Select.Root>
                    </FormField>

                    <!-- Samples tab -->

                    <Tabs.Content value="samples" class="pt-2">
                        <FormField label="Tag">
                            <Select.Root
                                type="single"
                                name="tagIdToExport"
                                bind:value={tagIdToExport}
                            >
                                <Select.Trigger class="w-full">
                                    {triggerContent}
                                </Select.Trigger>
                                <Select.Content>
                                    <Select.Group>
                                        <Select.GroupHeading>Annotation tags</Select.GroupHeading>
                                        {#if $tags.filter((tag) => tag.kind === 'annotation').length === 0}
                                            <div
                                                class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                                            >
                                                no tags available
                                            </div>
                                        {/if}
                                        {#each $tags.filter((tag) => tag.kind === 'annotation') as annotationTag}
                                            <Select.Item
                                                value={annotationTag.tag_id}
                                                label={annotationTag.name}
                                                >{annotationTag.name}</Select.Item
                                            >
                                        {/each}
                                        <Select.GroupHeading>Sample tags</Select.GroupHeading>
                                        {#if $tags.filter((tag) => tag.kind === 'sample').length === 0}
                                            <div
                                                class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                                            >
                                                no tags available
                                            </div>
                                        {/if}
                                        {#each $tags.filter((tag) => tag.kind === 'sample') as sampleTag}
                                            <Select.Item
                                                value={sampleTag.tag_id}
                                                label={sampleTag.name}>{sampleTag.name}</Select.Item
                                            >
                                        {/each}
                                    </Select.Group>
                                </Select.Content>
                            </Select.Root>
                        </FormField>

                        <div class="my-4">
                            <Checkbox
                                name="inverse-selection"
                                label="Inverse selection"
                                isChecked={isSelectionInverted}
                                onCheckedChange={() => (isSelectionInverted = !isSelectionInverted)}
                                helperText="Inverse selection will export all samples that are not selected"
                                disabled={isSubmitDisabled}
                            />
                        </div>

                        {#if isInfoEnabled}
                            <div class="my-4 rounded-lg bg-muted p-4">
                                <h4 class="font-medium">Summary</h4>
                                <div class="mt-2 text-sm text-muted-foreground">
                                    <p>Samples to export: <strong>{$count}</strong></p>
                                </div>
                            </div>
                        {/if}

                        {#if errorMessage}
                            <div transition:fade>
                                <Alert.Root
                                    variant="destructive"
                                    class="border text-foreground"
                                    data-testid={errorMessage
                                        ? 'alert-destructive'
                                        : 'alert-success'}
                                >
                                    <div class="flex items-center gap-2">
                                        <span class="text-destructive-foreground"
                                            >{errorMessage}</span
                                        >
                                    </div>
                                </Alert.Root>
                            </div>
                        {/if}

                        <Button
                            class="relative my-4 w-full"
                            disabled={isSubmitDisabled || $isLoading}
                            onclick={handleExport}
                            data-testid="submit-button-samples"
                        >
                            Download
                            {#if $isLoading}
                                <div
                                    class="absolute inset-0 flex items-center justify-center backdrop-blur-sm"
                                    data-testid="loading-spinner"
                                >
                                    <Loader2 class="animate-spin" />
                                </div>
                            {/if}
                        </Button>
                    </Tabs.Content>

                    <!-- Object Detections tab -->
                    <Tabs.Content value="object_detections" class="pt-2">
                        <p class="text-sm text-muted-foreground">
                            The object detection annotations will be exported in COCO format.
                        </p>

                        <Button
                            class="relative my-4 w-full"
                            href={exportAnnotationsURL}
                            target="_blank"
                            data-testid="submit-button-annotations"
                        >
                            Download
                        </Button>
                    </Tabs.Content>

                    <Tabs.Content value="segmentation" class="pt-2">
                        <p class="text-sm text-muted-foreground">
                            The segmentation masks will be exported in COCO format.
                        </p>

                        <Button
                            class="relative my-4 w-full"
                            href={exportSegmentationMaskURL}
                            target="_blank"
                            data-testid="submit-button-instance-segmentations"
                        >
                            Download
                        </Button>
                    </Tabs.Content>

                    {#if isVideoCollection}
                        <Tabs.Content value="youtube_vis_segmentation" class="pt-2">
                            <p class="text-sm text-muted-foreground">
                                The video segmentation masks will be exported in YouTube-VIS format.
                            </p>

                            <Button
                                class="relative my-4 w-full"
                                href={exportYoutubeVisSegmentationMaskURL}
                                target="_blank"
                                data-testid="submit-button-youtube-vis-instance-segmentations"
                            >
                                Download
                            </Button>
                        </Tabs.Content>
                    {/if}
                    <Tabs.Content value="semantic_segmentations" class="pt-2">
                        <p class="text-sm text-muted-foreground">
                            The semantic segmentations will be exported in PASCAL VOC format.
                        </p>

                        <Button
                            class="relative my-4 w-full"
                            href={exportPascalVocURL}
                            target="_blank"
                            data-testid="submit-button-semantic-segmentations"
                        >
                            Download
                        </Button>
                    </Tabs.Content>

                    <!-- Captions tab -->

                    <Tabs.Content value="captions" class="pt-2">
                        <p class="text-sm text-muted-foreground">
                            The captions will be exported in COCO format.
                        </p>

                        <Button
                            class="relative my-4 w-full"
                            href={exportCaptionsURL}
                            target="_blank"
                            data-testid="submit-button-captions"
                        >
                            Download
                        </Button>
                    </Tabs.Content>
                </Tabs.Root>
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
