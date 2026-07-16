<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        sample: { annotations: AnnotationView[] };
        showLabel?: boolean;
    }

    let { sample, showLabel = true }: Props = $props();
</script>

<div
    data-testid="mock-sample-classification-pills"
    data-show-label={showLabel}
    data-annotation-count={sample.annotations.length}
    data-annotation-ids={sample.annotations.map((annotation) => annotation.sample_id).join(',')}
></div>
