<script lang="ts">
    import { page } from '$app/state';
    import { FormField, AnnotationSourceSelect } from '$lib/components';
    import { exportCollectionAnnotationsPrepare } from '$lib/api/lightly_studio_local';
    import { useImageFilters } from '$lib/hooks';
    import { useVideoFilters } from '$lib/hooks';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import { useExportDownload, triggerDownload } from '../useExportDownload';
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
        /** Sample type whose annotations are being exported. */
        sampleType: 'image' | 'video';
        /** Optional callback invoked when the download button is clicked. */
        onDownloadClick?: () => void;
    }

    let {
        exportFormat,
        description,
        annotationSources,
        selectedAnnotationCollectionId = $bindable(),
        testId,
        sampleType,
        onDownloadClick
    }: Props = $props();

    const collectionId = page.params.collection_id!;
    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();

    const { isLoading, errorMessage, handleDownload } = useExportDownload(async () => {
        const activeFilter =
            sampleType === 'video'
                ? { video_filter: $videoFilter }
                : { image_filter: $imageFilter };
        const response = await exportCollectionAnnotationsPrepare({
            path: { collection_id: collectionId },
            body: {
                export_format: exportFormat,
                annotation_collection_id:
                    selectedAnnotationCollectionId ?? annotationSources[0]?.id,
                ...activeFilter
            }
        });
        if (response.error) throw new Error(JSON.stringify(response.error));
        const exportKey = response.data?.export_key;
        if (!exportKey) throw new Error('Unexpected empty response data');
        triggerDownload(
            `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/download/${exportKey}`
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
