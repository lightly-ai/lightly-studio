<script lang="ts">
    import type { AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';

    interface Props {
        annotation: AnnotationWithPayloadView;
        selected?: boolean;
    }

    let { annotation, selected = false }: Props = $props();
</script>

<div
    data-testid="mock-classification-grid-item"
    data-annotation-id={annotation.annotation.sample_id}
    data-selected={selected}
></div>
