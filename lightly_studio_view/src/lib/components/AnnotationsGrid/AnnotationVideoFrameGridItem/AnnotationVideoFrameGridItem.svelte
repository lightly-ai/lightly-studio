<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { AnnotationView, VideoFrameAnnotationView } from '$lib/api/lightly_studio_local';
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

    const sample = $derived({
        width: videoFrame.video.width,
        height: videoFrame.video.height,
        url: `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id}?compressed=true`
    });
</script>

<AnnotationItem {annotation} {containerHeight} {sample} {containerWidth} {showLabel} {selected} />
