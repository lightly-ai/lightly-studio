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
    import { Download } from '@lucide/svelte';
    import SidePanel from '../SidePanel/SidePanel.svelte';
    import { useExportSamplesCount } from './useExportSamplesCount/useExportSamplesCount';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';

    let isOpened = $state(false);
    let isSelectionInverted = $state(false);

    let datasetId = page.params.dataset_id;
    let tagIdToExport = $state('');

    const { tags } = useTags({ dataset_id: datasetId });

    const triggerContent = $derived(
        $tags.find((f) => f.tag_id === tagIdToExport)?.name ??
            "Select a tag to export it's samples (required)"
    );

    let exportType = $state<'annotations' | 'samples'>('samples');

    const filter = $derived.by(() => {
        const filter: ExportFilter = {};
        // Only "Samples" export mode supports filtering by selected samples.
        if (exportType === 'samples') {
            filter.tag_ids = tagIdToExport ? [tagIdToExport] : undefined;
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

    // enable info panel if there are selected samples or annotations or tag is selected
    const isInfoEnabled = $derived(exportType === 'samples' ? tagIdToExport : false);

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

    const getExportAnnotationsURL = (datasetId: string) => {
        // Add timestamp to avoid caching of the URL
        return `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/datasets/${datasetId}/export/annotations?ts=${Date.now()}`;
    };

    const handleExport = () => {
        // If we have ready to use url download we don't need to call exportDataset
        if (!exportURL) {
            exportDataset({
                dataset_id: datasetId,
                includeFilter,
                excludeFilter
            });
        }
    };

    const exportURL = $derived(
        exportType === 'annotations' ? getExportAnnotationsURL(datasetId) : undefined
    );
</script>

<Button variant="ghost" class="flex items-center space-x-2" onclick={() => (isOpened = true)}>
    <Download class="size-4" />
    Export & Download
</Button>

<SidePanel
    title="Export"
    submitLabel={'Download'}
    isOpen={isOpened}
    isDisabled={isSubmitDisabled}
    isLoading={$isLoading}
    {errorMessage}
    onSubmit={handleExport}
    {exportURL}
    onOpenChange={(open) => (isOpened = open)}
>
    <div class="space-y-6">
        <Tabs.Root bind:value={exportType} class="w-full">
            <Tabs.List class="grid w-full grid-cols-2">
                <Tabs.Trigger value="samples">Samples</Tabs.Trigger>
                <Tabs.Trigger value="annotations">Samples & Annotations</Tabs.Trigger>
            </Tabs.List>

            <Tabs.Content value="samples" class="pt-2">
                <FormField label="Tag">
                    <Select.Root type="single" name="tagIdToExport" bind:value={tagIdToExport}>
                        <Select.Trigger class="w-full">
                            {triggerContent}
                        </Select.Trigger>
                        <Select.Content>
                            <Select.Group>
                                <Select.GroupHeading>Annotation tags</Select.GroupHeading>
                                {#if $tags.filter((tag) => tag.kind == 'annotation').length === 0}
                                    <div
                                        class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                                    >
                                        no tags available
                                    </div>
                                {/if}
                                {#each $tags.filter((tag) => tag.kind == 'annotation') as annotationTag}
                                    <Select.Item
                                        value={annotationTag.tag_id}
                                        label={annotationTag.name}>{annotationTag.name}</Select.Item
                                    >
                                {/each}
                                <Select.GroupHeading>Sample tags</Select.GroupHeading>
                                {#if $tags.filter((tag) => tag.kind == 'sample').length === 0}
                                    <div
                                        class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                                    >
                                        no tags available
                                    </div>
                                {/if}
                                {#each $tags.filter((tag) => tag.kind == 'sample') as sampleTag}
                                    <Select.Item value={sampleTag.tag_id} label={sampleTag.name}
                                        >{sampleTag.name}</Select.Item
                                    >
                                {/each}
                            </Select.Group>
                        </Select.Content>
                    </Select.Root>
                </FormField>
            </Tabs.Content>

            <Tabs.Content value="annotations" class="pt-2">
                <p class="text-sm text-muted-foreground">
                    The annotations will be exported in COCO format along with the corresponding
                    samples. Currently, only object detection annotations can be exported.
                </p>
            </Tabs.Content>
        </Tabs.Root>

        {#if exportType === 'samples'}
            <div class="space-y-2">
                <Checkbox
                    name="inverse-selection"
                    label="Inverse selection"
                    isChecked={isSelectionInverted}
                    onCheckedChange={() => (isSelectionInverted = !isSelectionInverted)}
                    helperText="Inverse selection will export all samples that are not selected"
                    disabled={isSubmitDisabled}
                />
            </div>
        {/if}

        {#if isInfoEnabled}
            <div class="rounded-lg bg-muted p-4">
                <h4 class="font-medium">Summary</h4>
                <div class="mt-2 space-y-2 text-sm text-muted-foreground">
                    <p>Samples to export: <strong>{$count}</strong></p>
                </div>
            </div>
        {/if}
    </div>
</SidePanel>
