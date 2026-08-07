<script lang="ts">
    import { page } from '$app/state';
    import FormField from '$lib/components/FormField/FormField.svelte';
    import { Select, SelectMenuItem } from '$lib/components/Select';
    import * as Tabs from '$lib/components/ui/tabs/index.js';
    import * as Dialog from '$lib/components/ui/dialog';
    import { ExportFormat } from '$lib/api/lightly_studio_local';
    import { useAnnotationCollections, useExportDialog, useGlobalStorage } from '$lib/hooks';
    import { useExportTracking } from './useExportTracking/useExportTracking';
    import SamplesTab from './SamplesTab/SamplesTab.svelte';
    import AnnotationsTab from './AnnotationsTab/AnnotationsTab.svelte';
    import CaptionsTab from './CaptionsTab/CaptionsTab.svelte';
    import YoutubeVisTab from './YoutubeVisTab/YoutubeVisTab.svelte';
    import { getDefaultExportType, getExportOptions, type ExportType } from './exportOptions';

    const { isExportDialogOpen, openExportDialog, closeExportDialog } = useExportDialog();
    const { filteredSampleCount } = useGlobalStorage();
    const sampleCountLabel = $derived(
        `${$filteredSampleCount} ${$filteredSampleCount === 1 ? 'sample' : 'samples'}`
    );

    const isVideoCollection = $derived(
        page.data.collection?.sample_type === 'video' ||
            page.data.collection?.sample_type === 'video_frame'
    );
    const supportsVideoClassifications = $derived(page.data.collection?.sample_type === 'video');

    const collectionId = page.params.collection_id!;
    const tracking = useExportTracking({ collectionId });

    let exportType = $state<ExportType>('samples');

    let prevIsDialogOpen = $state(false);
    $effect(() => {
        const isOpen = $isExportDialogOpen;
        if (isOpen) {
            const defaultExportType = getDefaultExportType(page.data.collection?.sample_type);
            exportType = defaultExportType;
            if (!prevIsDialogOpen) {
                tracking.trackDialogDefaultFormatSet(defaultExportType);
            }
        }
        prevIsDialogOpen = isOpen;
    });

    const exportOptions = $derived(getExportOptions(page.data.collection?.sample_type));
    const exportTypeTriggerContent = $derived(
        exportOptions.find((option) => option.value === exportType)?.label ?? ''
    );

    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const annotationSources = $derived(
        (annotationCollectionsQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );
    let selectedAnnotationCollectionId = $state<string | undefined>(undefined);
</script>

<Dialog.Root
    open={$isExportDialogOpen}
    onOpenChange={(open) =>
        open
            ? openExportDialog({ collectionId })
            : closeExportDialog({ collectionId, exportFormat: exportType })}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="flex max-h-[75vh] flex-col border-border bg-background sm:max-w-[550px]"
        >
            <Dialog.Header>
                <Dialog.Title class="text-foreground">Collection Export</Dialog.Title>
            </Dialog.Header>
            <Dialog.Description class="text-foreground">
                Export <strong class="font-semibold text-primary">{sampleCountLabel}</strong> currently
                matching your filters.
            </Dialog.Description>

            <div class="grid flex-1 gap-4 overflow-y-auto px-1">
                <Tabs.Root bind:value={exportType} class="w-full">
                    <FormField label="Export Type">
                        <Select
                            value={exportType}
                            triggerLabel={exportTypeTriggerContent}
                            class="w-full"
                            testId="export-type-select"
                            onOpenChange={(open) =>
                                open && tracking.trackFormatSelectOpened(exportType)}
                            onValueChange={(v) => {
                                exportType = v as typeof exportType;
                                tracking.trackFormatSelected(v);
                            }}
                        >
                            {#snippet children()}
                                {#each exportOptions as option}
                                    <SelectMenuItem value={option.value} label={option.label}
                                        >{option.label}</SelectMenuItem
                                    >
                                {/each}
                            {/snippet}
                        </Select>
                    </FormField>

                    <Tabs.Content value="samples" class="pt-0">
                        <SamplesTab
                            onDownloadClick={() =>
                                tracking.handleAnnotationDownloadClick(exportType)}
                        />
                    </Tabs.Content>

                    <Tabs.Content value="classifications" class="pt-0">
                        <AnnotationsTab
                            exportFormat={ExportFormat.CLASSIFICATION_CSV}
                            description="The classification annotations will be exported in CSV format."
                            {annotationSources}
                            bind:selectedAnnotationCollectionId
                            testId="submit-button-classifications"
                            sampleType={supportsVideoClassifications ? 'video' : 'image'}
                            onDownloadClick={() =>
                                tracking.handleAnnotationDownloadClick(exportType)}
                        />
                    </Tabs.Content>

                    <Tabs.Content value="object_detections_coco" class="pt-0">
                        <AnnotationsTab
                            exportFormat={ExportFormat.OBJECT_DETECTION_COCO}
                            description="The object detection annotations will be exported in COCO format."
                            {annotationSources}
                            bind:selectedAnnotationCollectionId
                            testId="submit-button-annotations-coco"
                            sampleType="image"
                            onDownloadClick={() =>
                                tracking.handleAnnotationDownloadClick(exportType)}
                        />
                    </Tabs.Content>

                    <Tabs.Content value="object_detections_yolo" class="pt-0">
                        <AnnotationsTab
                            exportFormat={ExportFormat.OBJECT_DETECTION_YOLO}
                            description="The object detection annotations will be exported in YOLO format."
                            {annotationSources}
                            bind:selectedAnnotationCollectionId
                            testId="submit-button-annotations-yolo"
                            sampleType="image"
                            onDownloadClick={() =>
                                tracking.handleAnnotationDownloadClick(exportType)}
                        />
                    </Tabs.Content>

                    <Tabs.Content value="segmentation" class="pt-0">
                        <AnnotationsTab
                            exportFormat={ExportFormat.SEGMENTATION_MASK_COCO}
                            description="The segmentation masks will be exported in COCO format."
                            {annotationSources}
                            bind:selectedAnnotationCollectionId
                            testId="submit-button-instance-segmentations"
                            sampleType="image"
                            onDownloadClick={() =>
                                tracking.handleAnnotationDownloadClick(exportType)}
                        />
                    </Tabs.Content>

                    <Tabs.Content value="semantic_segmentations" class="pt-0">
                        <AnnotationsTab
                            exportFormat={ExportFormat.PASCAL_VOC}
                            description="The semantic segmentations will be exported in PASCAL VOC format."
                            {annotationSources}
                            bind:selectedAnnotationCollectionId
                            testId="submit-button-semantic-segmentations"
                            sampleType="image"
                            onDownloadClick={() =>
                                tracking.handleAnnotationDownloadClick(exportType)}
                        />
                    </Tabs.Content>

                    <Tabs.Content value="captions" class="pt-0">
                        <CaptionsTab
                            onDownloadClick={() =>
                                tracking.handleAnnotationDownloadClick(exportType)}
                        />
                    </Tabs.Content>

                    {#if isVideoCollection}
                        <Tabs.Content value="youtube_vis_segmentation" class="pt-0">
                            <YoutubeVisTab
                                onDownloadClick={() =>
                                    tracking.handleAnnotationDownloadClick(exportType)}
                            />
                        </Tabs.Content>
                    {/if}
                </Tabs.Root>
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
