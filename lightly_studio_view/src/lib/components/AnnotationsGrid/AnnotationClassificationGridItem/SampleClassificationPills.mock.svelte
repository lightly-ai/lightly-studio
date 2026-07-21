<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        sample: { annotations: AnnotationView[] };
    }

    let { sample }: Props = $props();
</script>

<div
    data-testid="mock-classification-pills"
    data-annotation-count={sample.annotations.length}
    data-annotation-id={sample.annotations[0]?.sample_id}
></div>
