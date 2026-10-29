<script lang="ts">
    import { type AnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        annotation: AnnotationView;
        isHidden?: boolean;
        colorBySource?: boolean;
        onToggleShowAnnotation: (e: MouseEvent) => void;
        onDragStart?: () => void;
        onDragEnd?: () => void;
    }

    let {
        annotation,
        isHidden = false,
        colorBySource,
        onToggleShowAnnotation,
        onDragStart,
        onDragEnd
    }: Props = $props();
</script>

<div
    data-testid="mock-annotation-row"
    data-annotation-id={annotation.sample_id}
    data-hidden={isHidden}
    data-color-by-source={colorBySource}
>
    <span>{annotation.annotation_label.annotation_label_name}</span>
    <button type="button" data-testid="mock-annotation-row-toggle" onclick={onToggleShowAnnotation}>
        {isHidden ? 'hidden' : 'visible'}
    </button>
    {#if onDragStart}
        <!-- No role, so that the row keeps a single button for the tests. -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            draggable="true"
            data-testid="mock-annotation-row-drag"
            ondragstart={onDragStart}
            ondragend={onDragEnd}
        ></div>
    {/if}
</div>
