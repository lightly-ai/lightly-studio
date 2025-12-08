<script lang="ts">
    import { page } from '$app/state';
    import FormField from '$lib/components/FormField/FormField.svelte';
    import { Checkbox } from '$lib/components';
    import { Button } from '$lib/components/ui';
    import * as Select from '$lib/components/ui/select/index.js';
    import * as Tabs from '$lib/components/ui/tabs/index.js';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { exportDataset } from '$lib/services/exportDataset';
    import type { ExportFilter } from '$lib/services/types';
    import { useExportSamplesCount } from './useExportSamplesCount/useExportSamplesCount';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Loader2 } from '@lucide/svelte';
    import * as Alert from '$lib/components/ui/alert/index.js';
    import { fade } from 'svelte/transition';
    import { useExportDialog } from '$lib/hooks/useExportDialog/useExportDialog';

    const { isExportDialogOpen, openExportDialog, closeExportDialog } = useExportDialog();

    let exportType = $state<'annotations' | 'samples'>('samples');
    let datasetId = page.params.dataset_id;

    //
    // Samples export
    //

    let isSelectionInverted = $state(false);
    let tagIdToExport = $state('');
    const { tags } = useTags({ dataset_id: datasetId });

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
            dataset_id: datasetId,
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
        const response = await exportDataset({
            dataset_id: datasetId,
            includeFilter,
            excludeFilter
        });
        if (response.error) {
            errorMessage = `Export failed: ${response.error}`;
        }
    };

    //
    // Annotations export
    //

    // TODO(Michal, 12/2025): Remove the function and use a variable.
    const getExportAnnotationsURL = (datasetId: string) => {
        // Add timestamp to avoid caching of the URL
        return `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/datasets/${datasetId}/export/annotations?ts=${Date.now()}`;
    };

    const exportURL = $derived(
        exportType === 'annotations' ? getExportAnnotationsURL(datasetId) : undefined
    );
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
                <Dialog.Title class="text-foreground">Dataset Export</Dialog.Title>
            </Dialog.Header>
            <Dialog.Description class="text-muted-foreground">
                Choose the export type:
            </Dialog.Description>

            <div class="grid flex-1 gap-4 overflow-y-auto px-1">
                <Tabs.Root bind:value={exportType} class="w-full">
                    <Tabs.List class="grid w-full grid-cols-2">
                        <Tabs.Trigger value="samples">Samples</Tabs.Trigger>
                        <Tabs.Trigger value="annotations">Samples & Annotations</Tabs.Trigger>
                    </Tabs.List>

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

                    <!-- Annotations tab -->

                    <Tabs.Content value="annotations" class="pt-2">
                        <p class="text-sm text-muted-foreground">
                            The annotations will be exported in COCO format along with the
                            corresponding samples. Currently, only object detection annotations can
                            be exported.
                        </p>

                        <Button
                            class="relative my-4 w-full"
                            disabled={isSubmitDisabled || $isLoading}
                            href={exportURL}
                            target="_blank"
                            data-testid="submit-button-annotations"
                        >
                            Download
                        </Button>
                    </Tabs.Content>
                </Tabs.Root>
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
