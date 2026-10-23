<script lang="ts">
    import { page } from '$app/state';
    import { exportCollectionYoutubeVisPrepare } from '$lib/api/lightly_studio_local';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import { useExportDownload, triggerDownload } from '../useExportDownload';
    import ExportDownloadButton from '../ExportDownloadButton/ExportDownloadButton.svelte';
    import { useVideoFilters } from '$lib/hooks';

    interface Props {
        onDownloadClick?: () => void;
        onExportTriggered?: (success: boolean) => void;
    }

    let { onDownloadClick, onExportTriggered }: Props = $props();

    const collectionId = page.params.collection_id!;
    const { videoFilter } = useVideoFilters();

    const { isLoading, errorMessage, handleDownload } = useExportDownload(async () => {
        const response = await exportCollectionYoutubeVisPrepare({
            path: { collection_id: collectionId },
            body: { video_filter: $videoFilter }
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
    <p class="text-sm text-muted-foreground">
        The video segmentation masks will be exported in YouTube-VIS format.
    </p>
    <ExportDownloadButton
        isLoading={$isLoading}
        errorMessage={$errorMessage}
        onclick={async () => {
            onDownloadClick?.();
            const success = await handleDownload();
            onExportTriggered?.(success);
        }}
        testId="submit-button-youtube-vis-instance-segmentations"
    />
</div>
