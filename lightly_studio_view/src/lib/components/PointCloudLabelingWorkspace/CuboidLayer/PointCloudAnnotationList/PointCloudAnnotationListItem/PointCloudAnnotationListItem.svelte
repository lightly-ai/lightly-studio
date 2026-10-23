<script lang="ts">
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';
    import PointCloudAnnotationDetails from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationDetails';
    import { Typography } from '$lib/components/Typography';
    import { ChevronDown, Trash2 } from '@lucide/svelte';
    import { cn } from '$lib/utils';
    import { Tooltip } from '$lib/components/ui/tooltip';

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
    <div class="flex w-full items-center">
        <button
            type="button"
            class="flex flex-1 items-center gap-2 px-4 py-3 text-left"
            onclick={() => onToggle(cuboid.id)}
            aria-expanded={isSelected}
            data-testid="point-cloud-annotation-list-row"
        >
            <span
                class="size-3 shrink-0 rounded-sm"
                style="background-color: {color}"
                aria-hidden="true"
            ></span>
            <Typography variant="body2" className="flex-1 truncate">{className}</Typography>
            {#if onDelete}
                <Tooltip content="Delete annotation">
                    <Trash2
                        class="size-4 shrink-0 text-muted-foreground hover:text-destructive"
                        onclick={(e) => {
                            e.stopPropagation();
                            onDelete(cuboid.id);
                        }}
                        data-testid="point-cloud-annotation-delete-button"
                    />
                </Tooltip>
            {/if}
            <ChevronDown
                class={cn(
                    'size-4 shrink-0 text-muted-foreground transition-transform',
                    isSelected && 'rotate-180'
                )}
            />
        </button>
    </div>
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
