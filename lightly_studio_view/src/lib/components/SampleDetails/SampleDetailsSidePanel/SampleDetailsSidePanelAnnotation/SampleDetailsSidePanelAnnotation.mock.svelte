<script lang="ts">
    import { type AnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        annotation: AnnotationView;
        isHidden?: boolean;
        onToggleShowAnnotation: (e: MouseEvent) => void;
    }

    let { annotation, isHidden = false, onToggleShowAnnotation }: Props = $props();
</script>

<div
    data-testid="mock-annotation-row"
    data-annotation-id={annotation.sample_id}
    data-hidden={isHidden}
>
    <span>{annotation.annotation_label.annotation_label_name}</span>
    <button type="button" data-testid="mock-annotation-row-toggle" onclick={onToggleShowAnnotation}>
        {isHidden ? 'hidden' : 'visible'}
    </button>
</div>
