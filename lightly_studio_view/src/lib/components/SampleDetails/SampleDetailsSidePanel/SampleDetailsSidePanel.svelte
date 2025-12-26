<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { type ImageView } from '$lib/api/lightly_studio_local';
    import { page } from '$app/state';
    import type { ListItem } from '$lib/components/SelectList/types';
    import SegmentTags from '$lib/components/SegmentTags/SegmentTags.svelte';
    import SampleDetailsAnnotationSegment from '../SampleDetailsAnnotationSegment/SampleDetailsAnnotationSegment.svelte';

    type Props = {
        sample: ImageView;
        selectedAnnotationId?: string;
        onUpdate: () => void;
        onDeleteCaption: (sampleId: string) => void;
        onCreateCaption: (sampleId: string) => void;
        onRemoveTag: (tagId: string) => void;
        addAnnotationEnabled: boolean;
        addAnnotationLabel: ListItem | undefined;
        annotationsIdsToHide: Set<string>;
        annotationType: string | null;
        collectionId: string;
        isPanModeEnabled: boolean;
    };
    let {
        addAnnotationEnabled = $bindable(false),
        addAnnotationLabel = $bindable<ListItem | undefined>(undefined),
        annotationType = $bindable<string | null>(undefined),
        selectedAnnotationId = $bindable<string | null>(),
        annotationsIdsToHide = $bindable<Set<string>>(),
        sample,
        onUpdate,
        onDeleteCaption,
        onCreateCaption,
        onRemoveTag,
        collectionId,
        isPanModeEnabled
    }: Props = $props();
    const tags = $derived(sample.tags.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);

    const { isEditingMode } = page.data.globalStorage;

    const captions = $derived(sample.captions ?? []);
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-y-auto dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <SampleDetailsAnnotationSegment
                bind:annotationType
                bind:addAnnotationEnabled
                bind:addAnnotationLabel
                bind:selectedAnnotationId
                bind:annotationsIdsToHide
                {collectionId}
                {isPanModeEnabled}
                refetch={onUpdate}
                annotations={sample.annotations}
            />
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
