<script lang="ts">
    import { page } from '$app/state';
    import { exportCollectionCaptionsPrepare } from '$lib/api/lightly_studio_local';
    import { useImageFilters } from '$lib/hooks';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import { useExportDownload, triggerDownload } from '../useExportDownload';
    import ExportDownloadButton from '../ExportDownloadButton/ExportDownloadButton.svelte';

    interface Props {
        onDownloadClick?: () => void;
    }

    let { onDownloadClick }: Props = $props();

    const collectionId = page.params.collection_id!;
    const { imageFilter } = useImageFilters();

    const { isLoading, errorMessage, handleDownload } = useExportDownload(async () => {
        const response = await exportCollectionCaptionsPrepare({
            path: { collection_id: collectionId },
            body: { image_filter: $imageFilter }
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
    <p class="text-sm text-muted-foreground">The captions will be exported in COCO format.</p>
    <ExportDownloadButton
        isLoading={$isLoading}
        errorMessage={$errorMessage}
        onclick={() => {
            onDownloadClick?.();
            handleDownload();
        }}
        testId="submit-button-captions"
    />
</div>
