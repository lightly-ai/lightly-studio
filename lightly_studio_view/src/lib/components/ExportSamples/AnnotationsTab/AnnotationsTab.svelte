<script lang="ts">
    import { page } from '$app/state';
    import { FormField, AnnotationSourceSelect } from '$lib/components';
    import { exportCollectionAnnotationsPrepare } from '$lib/api/lightly_studio_local';
    import { useImageFilters } from '$lib/hooks';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import { useExportDownload } from '../useExportDownload/useExportDownload';
    import ExportDownloadButton from '../ExportDownloadButton/ExportDownloadButton.svelte';

    type ExportFormat = NonNullable<
        Parameters<typeof exportCollectionAnnotationsPrepare>[0]['body']['export_format']
    >;

    interface Props {
        /** The format used when exporting annotations. */
        exportFormat: ExportFormat;
        /** Descriptive text shown above the export controls. */
        description: string;
        /** List of available annotation sources to export from. */
        annotationSources: { id: string; name: string }[];
        /** The ID of the currently selected annotation collection. Bindable. */
        selectedAnnotationCollectionId: string | undefined;
        /** Test ID applied to the download button for automated testing. */
        testId: string;
        /** Optional callback invoked when the download button is clicked. */
        onDownloadClick?: () => void;
    }

    let {
        exportFormat,
        description,
        annotationSources,
        selectedAnnotationCollectionId = $bindable(),
        testId,
        onDownloadClick
    }: Props = $props();

    const collectionId = page.params.collection_id!;
    const { imageFilter } = useImageFilters();

    const { isLoading, errorMessage, handleDownload } = useExportDownload(async () => {
        const response = await exportCollectionAnnotationsPrepare({
            path: { collection_id: collectionId },
            body: {
                export_format: exportFormat,
                annotation_collection_id:
                    selectedAnnotationCollectionId ?? annotationSources[0]?.id ?? undefined,
                image_filter: $imageFilter
            }
        });
        if (response.error) throw new Error(JSON.stringify(response.error));
        if (!response.data) return;
        window.open(
            `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/download/${response.data.export_key}`,
            '_blank'
        );
    });
</script>

<div class="pt-2">
    <p class="text-sm text-muted-foreground">{description}</p>

    {#if annotationSources.length > 1}
        <div class="mt-6">
            <FormField label="Annotation Source">
                <AnnotationSourceSelect
                    sourceOptions={annotationSources}
                    placeholder="Only annotations from the selected source will be exported"
                    bind:selectedSource={selectedAnnotationCollectionId}
                />
            </FormField>
        </div>
    {/if}

    <ExportDownloadButton
        isLoading={$isLoading}
        errorMessage={$errorMessage}
        onclick={() => {
            onDownloadClick?.();
            handleDownload();
        }}
        {testId}
    />
</div>
