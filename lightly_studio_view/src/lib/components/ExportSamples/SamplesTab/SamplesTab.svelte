<script lang="ts">
    import { page } from '$app/state';
    import { Checkbox } from '$lib/components';
    import FormField from '$lib/components/FormField/FormField.svelte';
    import {
        Select,
        SelectMenuItem,
        SelectMenuGroup,
        SelectMenuGroupHeading
    } from '$lib/components/Select';
    import { exportCollectionPrepare } from '$lib/api/lightly_studio_local';
    import { useTags, useImageFilters } from '$lib/hooks';
    import { useExportSamplesCount } from '../useExportSamplesCount/useExportSamplesCount.svelte';
    import { useExportDownload } from '../useExportDownload/useExportDownload';
    import ExportDownloadButton from '../ExportDownloadButton/ExportDownloadButton.svelte';
    import type { ExportFilter } from '$lib/services/types';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';

    const collectionId = page.params.collection_id;
    const { imageFilter } = useImageFilters();
    const { tags } = useTags({ collection_id: collectionId });

    let tagIdToExport = $state('');
    let isSelectionInverted = $state(false);

    const triggerContent = $derived(
        $tags.find((t) => t.tag_id === tagIdToExport)?.name ??
            'Select a tag to export its samples (required)'
    );

    const filter = $derived.by(() => {
        const f: ExportFilter = {};
        if (tagIdToExport) f.tag_ids = [tagIdToExport];
        return f;
    });
    const includeFilter = $derived(
        !isSelectionInverted && Object.keys(filter).length > 0 ? filter : undefined
    );
    const excludeFilter = $derived(
        isSelectionInverted && Object.keys(filter).length > 0 ? filter : undefined
    );

    const {
        isLoading: countIsLoading,
        error: statError,
        count
    } = useExportSamplesCount(() => ({
        collection_id: collectionId,
        includeFilter,
        excludeFilter,
        collectionFilter: $imageFilter
    }));

    const isSubmitDisabled = $derived(!tagIdToExport || !!$statError);

    const {
        isLoading: exportIsLoading,
        errorMessage,
        handleDownload: handleExport
    } = useExportDownload(async () => {
        const response = await exportCollectionPrepare({
            path: { collection_id: collectionId },
            body: {
                include: includeFilter,
                exclude: excludeFilter,
                collection_filter: $imageFilter
            }
        });
        if (response.error) throw new Error(JSON.stringify(response.error));
        window.open(
            `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/download/${response.data!.export_key}`,
            '_blank'
        );
    });
</script>

<div class="pt-2">
    <FormField label="Tag">
        <Select
            value={tagIdToExport}
            triggerLabel={triggerContent}
            class="w-full"
            onValueChange={(v) => (tagIdToExport = v)}
        >
            {#snippet children()}
                <SelectMenuGroup>
                    <SelectMenuGroupHeading>Annotation tags</SelectMenuGroupHeading>
                    {#each $tags.filter((t) => t.kind === 'annotation') as tag}
                        <SelectMenuItem value={tag.tag_id} label={tag.name}
                            >{tag.name}</SelectMenuItem
                        >
                    {:else}
                        <p class="px-2 py-1.5 text-sm text-muted-foreground">
                            No annotation tags available
                        </p>
                    {/each}
                    <SelectMenuGroupHeading>Sample tags</SelectMenuGroupHeading>
                    {#each $tags.filter((t) => t.kind === 'sample') as tag}
                        <SelectMenuItem value={tag.tag_id} label={tag.name}
                            >{tag.name}</SelectMenuItem
                        >
                    {:else}
                        <p class="px-2 py-1.5 text-sm text-muted-foreground">
                            No sample tags available
                        </p>
                    {/each}
                </SelectMenuGroup>
            {/snippet}
        </Select>
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

    {#if tagIdToExport || $imageFilter}
        <div class="my-4 rounded-lg bg-muted p-4">
            <h4 class="font-medium">Summary</h4>
            <p class="mt-2 text-sm text-muted-foreground">
                Samples to export: <strong>{$count}</strong>
            </p>
        </div>
    {/if}

    <ExportDownloadButton
        isLoading={$exportIsLoading || $countIsLoading}
        disabled={isSubmitDisabled}
        errorMessage={$statError ?? $errorMessage}
        onclick={handleExport}
        testId="submit-button-samples"
    />
</div>
