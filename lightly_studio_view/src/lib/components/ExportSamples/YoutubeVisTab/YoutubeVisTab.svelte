<script lang="ts">
    import { page } from '$app/state';
    import { exportCollectionYoutubeVisPrepare } from '$lib/api/lightly_studio_local';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import { useExportDownload, triggerDownload } from '../useExportDownload';
    import ExportDownloadButton from '../ExportDownloadButton/ExportDownloadButton.svelte';
    import { useVideoFilters } from '$lib/hooks';

    interface Props {
        onDownloadClick?: () => void;
    }

    let { onDownloadClick }: Props = $props();

    const collectionId = page.params.collection_id!;
    const { videoFilter } = useVideoFilters();
    // The video filter store keeps the last filter of the videos grid. A frame collection
    // exports all videos of its parent, because frame filters do not apply to whole videos.
    const isFrameCollection = page.data?.collection?.sample_type === 'video_frame';

    const { isLoading, errorMessage, handleDownload } = useExportDownload(async () => {
        const response = await exportCollectionYoutubeVisPrepare({
            path: { collection_id: collectionId },
            body: { video_filter: isFrameCollection ? null : $videoFilter }
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
        onclick={() => {
            onDownloadClick?.();
            handleDownload();
        }}
        testId="submit-button-youtube-vis-instance-segmentations"
    />
</div>
