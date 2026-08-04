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
        exportFormat: ExportFormat;
        description: string;
        annotationSources: { id: string; name: string }[];
        selectedAnnotationCollectionId: string | undefined;
        testId: string;
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

    const collectionId = page.params.collection_id;
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
