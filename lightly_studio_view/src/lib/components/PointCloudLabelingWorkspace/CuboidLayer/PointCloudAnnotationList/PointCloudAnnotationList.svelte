<script lang="ts">
    import type {
        AnnotationClass,
        AnnotationSource,
        CuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import {
        groupAnnotationsBySource,
        resolveAnnotationClassName
    } from './pointCloudAnnotationList';
    import { resolveCuboidColor } from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/cuboidColors';
    import PointCloudAnnotationListGroup from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationListGroup';
    import PointCloudAnnotationListItem from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationListItem';
    import { Typography } from '$lib/components/Typography';

    interface Props {
        /** Cuboid annotations to render. */
        cuboids: readonly CuboidAnnotation[];
        /** Classes used to resolve each cuboid's color and name. */
        annotationClasses: readonly AnnotationClass[];
        /** Sources used to group cuboids by origin. */
        annotationSources: readonly AnnotationSource[];
        /** ID of the currently expanded annotation row; bindable. */
        selectedCuboidId: string | null;
    }

    let {
        cuboids,
        annotationClasses,
        annotationSources,
        selectedCuboidId = $bindable(null)
    }: Props = $props();

    const groups = $derived(groupAnnotationsBySource({ cuboids, sources: annotationSources }));

    function toggle(id: string): void {
        selectedCuboidId = selectedCuboidId === id ? null : id;
    }
</script>

{#snippet annotationRows(items: readonly CuboidAnnotation[])}
    {#each items as cuboid (cuboid.id)}
        <PointCloudAnnotationListItem
            {cuboid}
            color={resolveCuboidColor(annotationClasses, cuboid.annotationClassId)}
            className={resolveAnnotationClassName({
                annotationClasses,
                annotationClassId: cuboid.annotationClassId
            })}
            isSelected={selectedCuboidId === cuboid.id}
            onToggle={toggle}
        />
    {/each}
{/snippet}

{#if cuboids.length === 0}
    <div class="flex h-full items-center justify-center">
        <Typography variant="body2" className="text-muted-foreground">No annotations</Typography>
    </div>
{:else if groups.length <= 1}
    <div class="space-y-1">
        {@render annotationRows(groups[0]?.cuboids ?? [])}
    </div>
{:else}
    <div class="space-y-2">
        {#each groups as group (group.sourceId)}
            <PointCloudAnnotationListGroup name={group.sourceName} count={group.cuboids.length}>
                <div class="space-y-1">
                    {@render annotationRows(group.cuboids)}
                </div>
            </PointCloudAnnotationListGroup>
        {/each}
    </div>
{/if}
