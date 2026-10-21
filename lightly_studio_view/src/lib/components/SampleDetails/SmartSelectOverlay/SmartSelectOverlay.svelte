<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import SampleAnnotationRect from '$lib/components/SampleDetails/SampleAnnotationRect/SampleAnnotationRect.svelte';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import NormalizedBoxRect from '$lib/components/SampleDetails/NormalizedBoxRect/NormalizedBoxRect.svelte';
    import SmartSelectPoints from './SmartSelectPoints.svelte';
    import { getClassNameAtPoint } from './SmartSelectOverlay.helpers';
    import { useDragBox } from '$lib/components/SampleDetails/useDragBox/useDragBox.svelte';
    import { useSmartSelect } from './useSmartSelect.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        collectionId: string;
        sampleId: string;
        sample: { width: number; height: number; annotations: AnnotationView[] };
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        saveAs: SaveAs;
        annotationClass?: string | null;
        annotationSource?: string | null;
        onActionsChange: (actions: {
            canSave: boolean;
            save: () => void;
            clear: () => void;
        }) => void;
    }

    let {
        collectionId,
        sampleId,
        sample,
        interactionRect = $bindable(),
        refetch,
        saveAs,
        annotationClass,
        annotationSource,
        onActionsChange
    }: Props = $props();

    const smartSelect = useSmartSelect(() => ({
        collectionId,
        sampleId,
        saveAs,
        annotationClass,
        annotationSource,
        onSaved: refetch
    }));
    const drag = useDragBox(() => ({ interactionRect }));
    const save = () => void smartSelect.save();

    $effect(() => {
        onActionsChange({ canSave: smartSelect.canSave, save, clear: smartSelect.clear });
    });

    const onPointerUp = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        const { start, box } = drag.onPointerUp(event);
        if (box) {
            smartSelect.selectBox(box);
            return;
        }
        if (!start) return;
        // Shift-click adds a negative point.
        const point = { ...start, positive: !event.shiftKey };
        smartSelect.addPoint(point, getClassNameAtPoint(sample.annotations, point, sample));
    };

    const onKeyDown = (event: KeyboardEvent) => {
        // Keys typed in a field or the pop-up must not save or clear.
        if (isTextInputTarget(event.target) || isOverlayTarget(event.target)) return;
        if (event.key === 'Enter' && smartSelect.canSave) {
            event.preventDefault();
            save();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            smartSelect.clear();
        }
    };
</script>

<svelte:window onkeydown={onKeyDown} />

{#if smartSelect.preview}
    <AnnotationPreview preview={smartSelect.preview} image={sample} {saveAs} />
{/if}
{#if drag.box}
    <NormalizedBoxRect box={drag.box} image={sample} dashed />
{/if}
<SmartSelectPoints points={smartSelect.points} image={sample} />
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointerdown={drag.onPointerDown}
    onpointermove={drag.onPointerMove}
    onpointerup={onPointerUp}
    onpointercancel={drag.onPointerCancel}
/>
