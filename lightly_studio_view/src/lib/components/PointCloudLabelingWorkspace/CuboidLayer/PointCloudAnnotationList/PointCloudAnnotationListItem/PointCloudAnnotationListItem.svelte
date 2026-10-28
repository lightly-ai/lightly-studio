<script lang="ts">
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';
    import PointCloudAnnotationDetails from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationDetails';
    import PointCloudAnnotationHeader from './PointCloudAnnotationHeader';
    import { cn } from '$lib/utils';

    interface Props {
        /** Cuboid displayed by this row. */
        cuboid: CuboidAnnotation;
        /** Display color resolved from the cuboid's annotation class. */
        color: string;
        /** Display name resolved from the cuboid's annotation class. */
        className: string;
        /** Whether this row's details are visible. */
        isSelected: boolean;
        /** Human-readable annotation source name, when available. */
        annotationSourceName?: string;
        /** When true, numeric fields in the detail panel become editable. */
        editable?: boolean;
        /** Toggles the row's expanded state. */
        onToggle: (cuboidId: string) => void;
        /** Called when the user commits a geometry change in the detail panel. */
        onCuboidTransform?: ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform'];
        /** Called when the user selects a new annotation class for this cuboid. */
        onLabelChange?: (
            annotationId: string,
            labelName: string,
            annotationSourceId: string
        ) => void;
        /** Deletes this cuboid annotation. */
        onDelete?: (cuboidId: string) => void;
    }

    let {
        cuboid,
        color,
        className,
        isSelected,
        annotationSourceName,
        editable = false,
        onToggle,
        onCuboidTransform,
        onLabelChange,
        onDelete
    }: Props = $props();

    function handleAnnotationChange(
        updated: Pick<CuboidAnnotation, 'center' | 'size' | 'rotation'>
    ) {
        onCuboidTransform?.({
            annotationId: cuboid.id,
            frameId: cuboid.frameId,
            center: updated.center,
            size: updated.size,
            rotation: updated.rotation
        });
    }
</script>

<div
    class={cn(
        'rounded-sm transition-colors',
        isSelected ? 'border border-accent-foreground/20 bg-accent' : 'bg-card hover:bg-accent/50'
    )}
>
    <PointCloudAnnotationHeader
        collectionId={cuboid.annotationSourceId}
        {color}
        {className}
        {isSelected}
        {editable}
        onToggle={() => onToggle(cuboid.id)}
        onLabelChange={(className) =>
            onLabelChange?.(cuboid.id, className, cuboid.annotationSourceId)}
        onDelete={onDelete ? () => onDelete(cuboid.id) : undefined}
    />
    {#if isSelected}
        <div class="px-4 pb-4 pt-1">
            <PointCloudAnnotationDetails
                {annotationSourceName}
                annotation={cuboid}
                {editable}
                onAnnotationChange={handleAnnotationChange}
            />
        </div>
    {/if}
</div>
