<script lang="ts">
    import type { AnnotationView, VideoFrameAnnotationView } from '$lib/api/lightly_studio_local';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getGridFrameURL, getGridThumbnailRequestSize } from '$lib/utils';
    import AnnotationItem from '../AnnotationItem/AnnotationItem.svelte';

    type Props = {
        annotation: AnnotationView;
        videoFrame: VideoFrameAnnotationView;
        containerWidth: number;
        containerHeight: number;
        showLabel: boolean;
        selected?: boolean;
    };

    let {
        annotation,
        containerWidth,
        containerHeight,
        videoFrame,
        showLabel = true,
        selected = false
    }: Props = $props();
    const { gridViewThumbnailQualityStore } = useSettings();

    const sample = $derived({
        width: videoFrame.video.width,
        height: videoFrame.video.height,
        url: getGridFrameURL({
            sampleId: videoFrame.sample_id,
            quality: $gridViewThumbnailQualityStore,
            renderedWidth: getGridThumbnailRequestSize(
                containerWidth,
                globalThis.window?.devicePixelRatio || 1
            ),
            renderedHeight: getGridThumbnailRequestSize(
                containerHeight,
                globalThis.window?.devicePixelRatio || 1
            )
        })
    });
</script>

<AnnotationItem {annotation} {containerHeight} {sample} {containerWidth} {showLabel} {selected} />
