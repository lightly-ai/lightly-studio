<script lang="ts">
    import { useAnnotationLabels } from "$lib/hooks/useAnnotationLabels/useAnnotationLabels";
    import { Segment } from "..";
    import LabelNotFound from "../LabelNotFound/LabelNotFound.svelte";
    import SampleDetailsSidePanelAnnotation from "../SampleDetails/SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte";
    import { getSelectionItems } from "../SelectList/getSelectionItems";
    import SelectList from "../SelectList/SelectList.svelte";
    import type { ListItem } from "../SelectList/types";
    import { Button } from "../ui";
    import { page } from '$app/state';

    type Props = {
        selectedAnnotationId?: string;
        onAnnotationClick: (annotationId: string) => void;
        onUpdate: () => void;
        onToggleShowAnnotation: (annotationId: string) => void;
        onDeleteAnnotation: (annotationId: string) => void;
        addAnnotationEnabled: boolean;
        addAnnotationLabel: ListItem | undefined;
        annotationsIdsToHide: Set<string>;
    };
    let {
        addAnnotationEnabled = $bindable(false),
        addAnnotationLabel = $bindable<ListItem | undefined>(undefined),
        selectedAnnotationId,
        onAnnotationClick,
        onUpdate,
        onToggleShowAnnotation,
        onDeleteAnnotation,
        annotationsIdsToHide
    }: Props = $props();

    const { isEditingMode } = page.data.globalStorage;
    const annotationLabels = useAnnotationLabels();
    const items = $derived(getSelectionItems($annotationLabels.data || []));

</script>
<Segment title="Annotations">
    <div class="flex flex-col gap-3 space-y-4">
        {#if $isEditingMode}
            <div class="items-left bg-muted mb-2 flex flex-col justify-between space-y-2 p-2">
                <div class="mb-2 w-full">
                    <Button
                        title="Add annotation"
                        variant={addAnnotationEnabled ? 'default' : 'outline'}
                        data-testid="create-rectangle"
                        class="w-full"
                        onclick={() => {
                            addAnnotationEnabled = !addAnnotationEnabled;
                        }}
                    >
                        Add annotation
                    </Button>
                </div>
                {#if addAnnotationEnabled}
                    <label class="text-muted-foreground flex w-full flex-col gap-3">
                        <div class="text-sm">Select or create a label for a new annotation.</div>
                        <SelectList
                            {items}
                            selectedItem={items.find((i) => i.value === addAnnotationLabel?.value)}
                            name="annotation-label"
                            label="Choose or create a label"
                            className="w-full"
                            contentClassName="w-full"
                            placeholder="Select or create a label"
                            onSelect={(item) => {
                                addAnnotationLabel = item;
                            }}
                        >
                            {#snippet notFound({ inputValue })}
                                <LabelNotFound label={inputValue} />
                            {/snippet}
                        </SelectList>
                    </label>
                {/if}
            </div>
        {/if}
        <div class="flex flex-col gap-2">
            <!-- {#each annotations as annotation}
                <SampleDetailsSidePanelAnnotation
                    {annotation}
                    isSelected={selectedAnnotationId === annotation.annotation_id}
                    onClick={() => onAnnotationClick(annotation.annotation_id)}
                    onDeleteAnnotation={() => onDeleteAnnotation(annotation.annotation_id)}
                    isHidden={annotationsIdsToHide.has(annotation.annotation_id)}
                    onToggleShowAnnotation={(e) => {
                        e.stopPropagation();
                        onToggleShowAnnotation(annotation.annotation_id);
                    }}
                    {onUpdate}
                />
            {/each} -->
        </div>
    </div>
</Segment>
