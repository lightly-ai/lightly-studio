<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
    import SampleDetailsSidePanelAnnotation from './SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { AnnotationType, type ImageView } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components/ui';
    import { page } from '$app/state';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import type { ListItem } from '$lib/components/SelectList/types';
    import SegmentTags from '$lib/components/SegmentTags/SegmentTags.svelte';

    type Props = {
        sample: ImageView;
        selectedAnnotationId?: string;
        onAnnotationClick: (annotationId: string) => void;
        onUpdate: () => void;
        onToggleShowAnnotation: (annotationId: string) => void;
        onDeleteAnnotation: (annotationId: string) => void;
        onDeleteCaption: (sampleId: string) => void;
        onCreateCaption: (sampleId: string) => void;
        onRemoveTag: (tagId: string) => void;
        addAnnotationEnabled: boolean;
        addAnnotationLabel: ListItem | undefined;
        annotationsIdsToHide: Set<string>;
        annotationType: string | null;
    };
    let {
        addAnnotationEnabled = $bindable(false),
        addAnnotationLabel = $bindable<ListItem | undefined>(undefined),
        annotationType = $bindable<string | null>(undefined),
        sample,
        selectedAnnotationId,
        onAnnotationClick,
        onUpdate,
        onToggleShowAnnotation,
        onDeleteAnnotation,
        onDeleteCaption,
        onCreateCaption,
        onRemoveTag,
        annotationsIdsToHide
    }: Props = $props();
    const tags = $derived(sample.tags.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);
    const annotations = $derived(
        sample.annotations
            ? [...sample.annotations].sort((a, b) =>
                  a.annotation_label.annotation_label_name.localeCompare(
                      b.annotation_label.annotation_label_name
                  )
              )
            : []
    );
    const { isEditingMode } = page.data.globalStorage;
    const annotationLabels = useAnnotationLabels();
    const items = $derived(getSelectionItems($annotationLabels.data || []));

    // Auto-scroll to selected annotation
    $effect(() => {
        if (selectedAnnotationId) {
            const element = document.querySelector(
                `button[data-annotation-id="${selectedAnnotationId}"]`
            );
            if (element) {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest',
                    inline: 'nearest'
                });
            }
        }
    });

    const captions = $derived(sample.captions ?? []);

    const annotationTypeItems = [
        {
            value: AnnotationType.OBJECT_DETECTION,
            label: 'Object detection'
        },
        {
            value: AnnotationType.INSTANCE_SEGMENTATION,
            label: 'Instance segmentation'
        }
    ];
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-y-auto dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <Segment title="Annotations">
                <div class="flex flex-col gap-3 space-y-4">
                    {#if $isEditingMode}
                        <div
                            class="items-left mb-2 flex flex-col justify-between space-y-2 bg-muted p-2"
                        >
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
                                <label class="flex w-full flex-col gap-3 text-muted-foreground">
                                    <div class="text-sm">Select an annotation type</div>
                                    <SelectList
                                        items={annotationTypeItems}
                                        selectedItem={annotationTypeItems.find(
                                            (i) => i.value === annotationType
                                        )}
                                        name="annotation-type"
                                        label="Choose annotation type"
                                        className="w-full"
                                        contentClassName="w-full"
                                        placeholder="Choose annotation type"
                                        onSelect={(item) => {
                                            annotationType = item.value;
                                        }}
                                    ></SelectList>
                                </label>
                                <label class="flex w-full flex-col gap-3 text-muted-foreground">
                                    <div class="text-sm">
                                        Select or create a label for a new annotation.
                                    </div>
                                    <SelectList
                                        {items}
                                        selectedItem={items.find(
                                            (i) => i.value === addAnnotationLabel?.value
                                        )}
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
                        {#each annotations as annotation}
                            <SampleDetailsSidePanelAnnotation
                                {annotation}
                                isSelected={selectedAnnotationId === annotation.sample_id}
                                onClick={() => onAnnotationClick(annotation.sample_id)}
                                onDeleteAnnotation={() => onDeleteAnnotation(annotation.sample_id)}
                                isHidden={annotationsIdsToHide.has(annotation.sample_id)}
                                onToggleShowAnnotation={(e) => {
                                    e.stopPropagation();
                                    onToggleShowAnnotation(annotation.sample_id);
                                }}
                                {onUpdate}
                            />
                        {/each}
                    </div>
                </div>
            </Segment>
            <Segment title="Captions">
                <div class="flex flex-col gap-3 space-y-4">
                    <div class="flex flex-col gap-2">
                        {#each captions as caption}
                            <CaptionField
                                {caption}
                                onDeleteCaption={() => onDeleteCaption(caption.sample_id)}
                                {onUpdate}
                            />
                        {/each}
                        <!-- Add new caption button -->
                        {#if $isEditingMode}
                            <button
                                type="button"
                                class="mb-2 flex h-8 items-center justify-center rounded-sm bg-card px-2 py-0 text-diffuse-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                                onclick={() => onCreateCaption(sample.sample_id)}
                                data-testid="add-caption-button"
                            >
                                +
                            </button>
                        {/if}
                    </div>
                </div>
            </Segment>

            <SampleMetadata {sample} />
        </div>
    </CardContent>
</Card>
