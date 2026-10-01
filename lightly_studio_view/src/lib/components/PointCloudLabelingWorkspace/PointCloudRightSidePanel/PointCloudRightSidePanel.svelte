<script lang="ts">
    import type {
        AnnotationClass,
        AnnotationSource,
        CuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import PointCloudAnnotationList from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList';

    interface Props {
        /** Cuboid annotations to display in the list. */
        cuboids?: readonly CuboidAnnotation[];
        /** Classes used to resolve each cuboid's color and name. */
        annotationClasses?: readonly AnnotationClass[];
        /** Sources used to group annotations by origin. */
        annotationSources?: readonly AnnotationSource[];
        /** ID of the currently expanded annotation row; bindable. */
        selectedCuboidId?: string | null;
    }

    let {
        cuboids = [],
        annotationClasses = [],
        annotationSources = [],
        selectedCuboidId = $bindable(null)
    }: Props = $props();
</script>

<div
    class="flex h-full flex-col overflow-y-auto border-l bg-background p-3 dark:[color-scheme:dark]"
    data-testid="point-cloud-right-side-panel"
>
    <div class="flex flex-1 flex-col">
        <PointCloudAnnotationList
            {cuboids}
            {annotationClasses}
            {annotationSources}
            bind:selectedCuboidId
        />
    </div>
</div>
