<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { AnnotationSourcePicker } from '$lib/components/AnnotationSourcePicker';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import { FolderInput, Trash2 } from '@lucide/svelte';
    import { placePanel } from './SelectedBoxPanel.helpers';
    import { useSelectedBoxActions } from './useSelectedBoxActions.svelte';

    interface Props {
        /** The collection that owns the annotation sources. */
        collectionId: string;
        annotation: AnnotationView;
        refetch: () => void;
    }

    const { collectionId, annotation, refetch }: Props = $props();
    const actions = useSelectedBoxActions(() => ({ collectionId, annotation, refetch }));
    const items = $derived(getSelectionItems(actions.labels.data ?? []));
    const labelName = $derived(annotation.annotation_label.annotation_label_name);
    const selectedItem = $derived(
        items.find((item) => item.value === labelName) ?? { value: labelName, label: labelName }
    );
    const sourceName = $derived(
        actions.sources.data?.find(
            (source) => source.collection_id === annotation.annotation_collection_id
        )?.name ?? 'Annotation source'
    );
    const isMoving = actions.isMoving;

    let panel: HTMLDivElement | undefined = $state();
    let position = $state<{ left: number; top: number } | null>(null);

    // Follow the box on screen. Pan, zoom and box edits all move it, so read its rectangle
    // every frame instead of listening to each of them.
    $effect(() => {
        const annotationId = annotation.sample_id;
        let last = '';
        let frame = 0;
        const update = () => {
            const box = document.querySelector(`g[data-group-id="${annotationId}"]`);
            const canvas = box?.closest('svg');
            const next =
                box && canvas && panel
                    ? placePanel({
                          box: box.getBoundingClientRect(),
                          canvas: canvas.getBoundingClientRect(),
                          panel: { width: panel.offsetWidth, height: panel.offsetHeight }
                      })
                    : null;
            const key = JSON.stringify(next);
            if (key !== last) {
                last = key;
                position = next;
            }
            frame = requestAnimationFrame(update);
        };
        frame = requestAnimationFrame(update);
        return () => cancelAnimationFrame(frame);
    });
</script>

<div
    bind:this={panel}
    class="fixed z-20 flex w-56 flex-col gap-2 rounded-md border bg-popover p-2 text-popover-foreground shadow-lg"
    style:left="{position?.left ?? 0}px"
    style:top="{position?.top ?? 0}px"
    style:visibility={position ? 'visible' : 'hidden'}
    data-testid="selected-box-panel"
>
    <SelectList
        {items}
        {selectedItem}
        name="selected-box-annotation-class"
        label="Annotation class"
        placeholder="Select or create a class"
        className="h-8 w-full min-w-0 px-3"
        contentClassName="w-full min-w-0"
        onSelect={(item) => actions.changeClass(item.value)}
    >
        {#snippet notFound({ inputValue })}
            <LabelNotFound label={inputValue} />
        {/snippet}
    </SelectList>
    <div class="flex items-center gap-2">
        <div class="min-w-0 flex-1">
            <AnnotationSourcePicker
                {collectionId}
                excludeSourceId={annotation.annotation_collection_id}
                label="Move to another annotation source"
                heading="Move to"
                icon={FolderInput}
                triggerText={sourceName}
                disabled={$isMoving}
                onPick={actions.moveTo}
            />
        </div>
        <button
            type="button"
            class="inline-flex size-9 shrink-0 items-center justify-center rounded-md border hover:bg-accent"
            aria-label="Delete annotation"
            title="Delete annotation"
            onclick={actions.remove}
        >
            <Trash2 class="size-4" />
        </button>
    </div>
</div>
