<script lang="ts">
    import { page } from '$app/state';
    import { exportCollectionYoutubeVisPrepare } from '$lib/api/lightly_studio_local';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import { useExportDownload } from '$lib/components/ExportSamples/useExportDownload/useExportDownload';
    import ExportDownloadButton from '$lib/components/ExportSamples/ExportDownloadButton/ExportDownloadButton.svelte';

    const collectionId = page.params.collection_id;

    const { isLoading, errorMessage, handleDownload } = useExportDownload(async () => {
        const response = await exportCollectionYoutubeVisPrepare({
            path: { collection_id: collectionId },
            body: { video_filter: null }
        });
        if (response.error) throw new Error(JSON.stringify(response.error));
        window.open(
            `${PUBLIC_LIGHTLY_STUDIO_API_URL}api/collections/${collectionId}/export/download/${response.data!.export_key}`,
            '_blank'
        );
    });
</script>

<div class="pt-2">
    <p class="text-sm text-muted-foreground">
        The video segmentation masks will be exported in YouTube-VIS format.
    </p>
    <ExportDownloadButton
        isLoading={$isLoading}
        errorMessage={$errorMessage}
        onclick={handleDownload}
        testId="submit-button-youtube-vis-instance-segmentations"
    />
</div>
