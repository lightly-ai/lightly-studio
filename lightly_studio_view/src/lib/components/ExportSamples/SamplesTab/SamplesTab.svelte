<script lang="ts">
    import { page } from '$app/state';
    import { exportCollectionPrepare } from '$lib/api/lightly_studio_local';
    import { useImageFilters } from '$lib/hooks';
    import { useExportDownload } from '../useExportDownload/useExportDownload';
    import ExportDownloadButton from '../ExportDownloadButton/ExportDownloadButton.svelte';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';

    interface Props {
        onDownloadClick?: () => void;
    }

    let { onDownloadClick }: Props = $props();

    const collectionId = page.params.collection_id!;
    const { imageFilter } = useImageFilters();

    const {
        isLoading: exportIsLoading,
        errorMessage,
        handleDownload: handleExport
    } = useExportDownload(async () => {
        const response = await exportCollectionPrepare({
            path: { collection_id: collectionId },
            body: {
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
    <ExportDownloadButton
        isLoading={$exportIsLoading}
        errorMessage={$errorMessage}
        onclick={() => {
            onDownloadClick?.();
            handleExport();
        }}
        testId="submit-button-samples"
    />
</div>
