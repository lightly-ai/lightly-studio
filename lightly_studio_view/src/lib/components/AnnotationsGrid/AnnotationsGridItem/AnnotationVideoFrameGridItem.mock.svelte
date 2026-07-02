<script lang="ts">
    import type { AnnotationView, VideoFrameAnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        annotation: AnnotationView;
        videoFrame: VideoFrameAnnotationView;
        containerWidth: number;
        containerHeight: number;
        showLabel: boolean;
        selected?: boolean;
    }

    let {
        videoFrame,
        containerWidth,
        containerHeight,
        showLabel,
        selected = false
    }: Props = $props();
</script>

<div
    data-testid="mock-video-grid-item"
    data-sample-id={videoFrame?.sample_id}
    data-container-width={containerWidth}
    data-container-height={containerHeight}
    data-show-label={showLabel}
    data-selected={selected}
></div>
