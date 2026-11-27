<script lang="ts">
    import { type AnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        annotation: AnnotationView;
        isHidden?: boolean;
        isLocked?: boolean;
        colorBySource?: boolean;
        onToggleShowAnnotation: (e: MouseEvent) => void;
        onToggleLock?: (e: MouseEvent) => void;
        onChangeAnnotationLabel?: (label: string) => void;
        onDeleteAnnotation?: () => void;
    }

    let {
        annotation,
        isHidden = false,
        isLocked = false,
        colorBySource,
        onToggleShowAnnotation,
        onToggleLock,
        onChangeAnnotationLabel,
        onDeleteAnnotation
    }: Props = $props();
</script>

<div
    data-testid="mock-annotation-row"
    data-annotation-id={annotation.sample_id}
    data-hidden={isHidden}
    data-locked={isLocked}
    data-color-by-source={colorBySource}
>
    <span>{annotation.annotation_label.annotation_label_name}</span>
    <button type="button" data-testid="mock-annotation-row-toggle" onclick={onToggleShowAnnotation}>
        {isHidden ? 'hidden' : 'visible'}
    </button>
    <button type="button" data-testid="mock-annotation-row-lock" onclick={onToggleLock}>
        {isLocked ? 'locked' : 'unlocked'}
    </button>
    <button
        type="button"
        data-testid="mock-annotation-row-relabel"
        onclick={() => onChangeAnnotationLabel?.('dog')}
    >
        relabel to dog
    </button>
    <button type="button" data-testid="mock-annotation-row-delete" onclick={onDeleteAnnotation}>
        delete
    </button>
</div>
