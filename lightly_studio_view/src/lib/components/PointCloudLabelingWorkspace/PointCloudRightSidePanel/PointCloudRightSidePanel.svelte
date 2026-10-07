<script lang="ts">
    import type {
        AnnotationClass,
        AnnotationSource,
        CuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import PointCloudAnnotationList from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList';
    import { Segment, SegmentTags } from '$lib/components';

    interface Props {
        /** Cuboid annotations to display in the list. */
        cuboids?: readonly CuboidAnnotation[];
        /** Classes used to resolve each cuboid's color and name. */
        annotationClasses?: readonly AnnotationClass[];
        /** Sources used to group annotations by origin. */
        annotationSources?: readonly AnnotationSource[];
        /** ID of the currently expanded annotation row; bindable. */
        selectedCuboidId?: string | null;
        /** Group sample of the active tick; the tags segment is hidden until it loads. */
        tick?: {
            sampleId: string;
            collectionId: string;
            tags: { tag_id?: string; name: string }[];
        };
        /** Reloads the tick after a tag is added or removed. */
        onTagsChange?: () => void;
    }

    let {
        cuboids = [],
        annotationClasses = [],
        annotationSources = [],
        selectedCuboidId = $bindable(null),
        tick,
        onTagsChange
    }: Props = $props();
</script>

<div
    class="scrollbar-thin flex h-full flex-col overflow-y-auto border-l bg-background p-3 dark:[color-scheme:dark]"
    data-testid="point-cloud-right-side-panel"
>
    <div class="flex flex-1 flex-col">
        {#if tick}
            {#key tick.sampleId}
                <SegmentTags
                    tags={tick.tags}
                    collectionId={tick.collectionId}
                    sampleId={tick.sampleId}
                    onRefetch={onTagsChange}
                />
            {/key}
        {/if}
        <Segment title="Annotations">
            <PointCloudAnnotationList
                {cuboids}
                {annotationClasses}
                {annotationSources}
                bind:selectedCuboidId
            />
        </Segment>
    </div>
</div>
