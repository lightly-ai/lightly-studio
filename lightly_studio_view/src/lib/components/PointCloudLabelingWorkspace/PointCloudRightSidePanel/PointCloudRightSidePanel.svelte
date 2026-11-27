<script lang="ts">
    import type {
        AnnotationClass,
        AnnotationSource,
        CuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';
    import PointCloudAnnotationList from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList';
    import { Segment, SegmentTags } from '$lib/components';
    import type { EgoRange } from '$lib/components/PointCloudLabelingWorkspace/EgoRange';

    interface Props {
        /** Cuboid annotations to display in the list. */
        cuboids?: readonly CuboidAnnotation[];
        /** Classes used to resolve each cuboid's color and name. */
        annotationClasses?: readonly AnnotationClass[];
        /** Sources used to group annotations by origin. */
        annotationSources?: readonly AnnotationSource[];
        /** ID of the currently expanded annotation row; bindable. */
        selectedCuboidId?: string | null;
        /** Sequence sample, the same one as in the sequences grid; hidden until it loads. */
        sequence?: {
            sampleId: string;
            collectionId: string;
            tags: { tag_id?: string; name: string }[];
        };
        /** Reloads the sequence after a tag is added or removed. */
        onSequenceTagsChange?: () => void;
        /** Group sample of the active tick; the tags segment is hidden until it loads. */
        tick?: {
            sampleId: string;
            collectionId: string;
            tags: { tag_id?: string; name: string }[];
            /** True while the tags still belong to the previous tick; editing is blocked. */
            isStale?: boolean;
        };
        /** Reloads the tick after a tag is added or removed. */
        onTagsChange?: () => void;
        /** When true, numeric fields in the selected annotation become editable. */
        editable?: boolean;
        /** Called when the user commits a geometry change in the detail panel. */
        onCuboidTransform?: ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform'];
        /** Called when the user selects a new annotation class for a cuboid. */
        onLabelChange?: (
            annotationId: string,
            labelName: string,
            annotationSourceId: string
        ) => void;
        /** Called after the annotation's track assignment changes. */
        onTrackChange?: () => Promise<void>;
        /** Deletes a cuboid annotation by ID. */
        onDeleteCuboid?: (cuboidId: string) => void;
        /** The source new cuboids go to. */
        targetSourceName?: string | null;
        /** A typed source name that is not created yet. */
        pendingSourceName?: string | null;
        /** Whether no source is picked among several. */
        needsPick?: boolean;
        /** Picks the source for new cuboids. Without it, the panel shows no source picker. */
        onPickSource?: (name: string, options?: { isNew?: boolean }) => void;
        /** True when the cuboid is hidden in the scene. */
        isCuboidHidden?: (cuboid: CuboidAnnotation) => boolean;
        /** True when every cuboid of the source is hidden in the scene. */
        isSourceHidden?: (sourceId: string) => boolean;
        /** Hides or shows the track of a cuboid. */
        onToggleTrackVisibility?: (cuboid: CuboidAnnotation) => void;
        /** Hides or shows every cuboid of a source. */
        onToggleSourceVisibility?: (sourceId: string) => void;
        /** Range around the ego; annotation rows show their distance while it is set. */
        egoRange?: EgoRange | null;
    }

    let {
        cuboids = [],
        annotationClasses = [],
        annotationSources = [],
        selectedCuboidId = $bindable(null),
        sequence,
        onSequenceTagsChange,
        tick,
        onTagsChange,
        editable = false,
        onCuboidTransform,
        onLabelChange,
        onTrackChange,
        onDeleteCuboid,
        isCuboidHidden,
        isSourceHidden,
        onToggleTrackVisibility,
        onToggleSourceVisibility,
        targetSourceName,
        pendingSourceName,
        needsPick,
        onPickSource,
        egoRange = null
    }: Props = $props();
</script>

<div
    class="scrollbar-thin flex h-full flex-col overflow-y-auto border-l bg-background p-3 dark:[color-scheme:dark]"
    data-testid="point-cloud-right-side-panel"
>
    <div class="flex flex-1 flex-col">
        {#if sequence}
            {#key sequence.sampleId}
                <SegmentTags
                    title="Sequence tags"
                    tags={sequence.tags}
                    collectionId={sequence.collectionId}
                    sampleId={sequence.sampleId}
                    onRefetch={onSequenceTagsChange}
                />
            {/key}
        {/if}
        {#if tick}
            <!-- Stays mounted while the next tick loads to keep the layout steady. -->
            <div inert={tick.isStale} data-testid="point-cloud-tick-tags">
                {#key tick.sampleId}
                    <SegmentTags
                        title="Frame tags"
                        tags={tick.tags}
                        collectionId={tick.collectionId}
                        sampleId={tick.sampleId}
                        onRefetch={onTagsChange}
                    />
                {/key}
            </div>
        {/if}
        <Segment title="Annotations">
            <PointCloudAnnotationList
                {cuboids}
                {annotationClasses}
                {annotationSources}
                bind:selectedCuboidId
                {editable}
                {onCuboidTransform}
                {onLabelChange}
                {onTrackChange}
                {onDeleteCuboid}
                sourcePicker={onPickSource
                    ? {
                          targetSourceName: targetSourceName ?? null,
                          pendingSourceName: pendingSourceName ?? null,
                          needsPick: needsPick ?? false,
                          onPick: onPickSource
                      }
                    : undefined}
                {isCuboidHidden}
                {isSourceHidden}
                {onToggleTrackVisibility}
                {egoRange}
                {onToggleSourceVisibility}
            />
        </Segment>
    </div>
</div>
