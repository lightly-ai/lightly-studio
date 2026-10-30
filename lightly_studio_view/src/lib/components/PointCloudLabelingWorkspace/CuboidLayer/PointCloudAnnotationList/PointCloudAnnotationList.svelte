<script lang="ts">
    import type {
        AnnotationClass,
        AnnotationSource,
        CuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';
    import {
        groupAnnotationsBySource,
        resolveAnnotationClassName,
        resolveAnnotationSourceName,
        buildAnnotationForest,
        NO_PARENT_TRACK_GROUP_LABEL
    } from './pointCloudAnnotationList';
    import { resolveCuboidColor } from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/cuboidColors';
    import PointCloudAnnotationListGroup from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationListGroup';
    import PointCloudAnnotationListItem from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationListItem';
    import PointCloudAnnotationParentGroup from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationParentGroup';
    import { Typography } from '$lib/components/Typography';

    type AnnotationTreeNode = ReturnType<typeof buildAnnotationForest>[number];

    interface Props {
        /** Cuboid annotations to render. */
        cuboids: readonly CuboidAnnotation[];
        /** Classes used to resolve each cuboid's color and name. */
        annotationClasses: readonly AnnotationClass[];
        /** Sources used to group cuboids by origin. */
        annotationSources: readonly AnnotationSource[];
        /** ID of the currently expanded annotation row; bindable. */
        selectedCuboidId: string | null;
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
        /** Deletes a cuboid annotation by ID. */
        onDeleteCuboid?: (cuboidId: string) => void;
    }

    let {
        cuboids,
        annotationClasses,
        annotationSources,
        selectedCuboidId = $bindable(null),
        editable = false,
        onCuboidTransform,
        onLabelChange,
        onDeleteCuboid
    }: Props = $props();

    const groups = $derived(groupAnnotationsBySource({ cuboids, sources: annotationSources }));

    function toggle(id: string): void {
        selectedCuboidId = selectedCuboidId === id ? null : id;
    }

    function forestNodeKey(node: AnnotationTreeNode): string {
        if (node.cuboid) return node.cuboid.id;
        const firstChild = node.children[0]?.cuboid;
        if (firstChild?.parentTrackClassName) return `absent-${firstChild.parentTrackNumber}`;
        return 'no-track';
    }
</script>

{#snippet annotationItem(cuboid: CuboidAnnotation)}
    <PointCloudAnnotationListItem
        {cuboid}
        color={resolveCuboidColor(annotationClasses, cuboid.annotationClassId)}
        className={resolveAnnotationClassName({
            annotationClasses,
            annotationClassId: cuboid.annotationClassId
        })}
        isSelected={selectedCuboidId === cuboid.id}
        annotationSourceName={resolveAnnotationSourceName({
            annotationSourceId: cuboid.annotationSourceId,
            sources: annotationSources
        })}
        onToggle={toggle}
        {editable}
        {onCuboidTransform}
        {onLabelChange}
        onDelete={onDeleteCuboid}
    />
{/snippet}

{#snippet childRows(children: readonly AnnotationTreeNode[])}
    {#each children as child (child.cuboid?.id ?? child.children[0]?.cuboid?.id)}
        {#if child.children.length > 0}
            <div class="pl-2 pt-2">
                {@render annotationNode(child)}
            </div>
        {:else}
            {@render annotationNode(child)}
        {/if}
    {/each}
{/snippet}

{#snippet annotationNode(node: AnnotationTreeNode)}
    {#if node.cuboid && node.children.length > 0}
        <PointCloudAnnotationParentGroup
            className={resolveAnnotationClassName({
                annotationClasses,
                annotationClassId: node.cuboid.annotationClassId
            })}
            trackNumber={node.cuboid.trackNumber}
            subtreeSize={node.subtreeSize}
        >
            <div class="space-y-1">
                {@render annotationItem(node.cuboid)}
                {@render childRows(node.children)}
            </div>
        </PointCloudAnnotationParentGroup>
    {:else if !node.cuboid && node.children.length > 0}
        {@const firstChild = node.children[0].cuboid}
        {#if firstChild}
            <PointCloudAnnotationParentGroup
                className={firstChild.parentTrackClassName ?? NO_PARENT_TRACK_GROUP_LABEL}
                trackNumber={firstChild.parentTrackClassName ? firstChild.parentTrackNumber : null}
                subtreeSize={node.subtreeSize}
            >
                <div class="space-y-1">
                    {@render childRows(node.children)}
                </div>
            </PointCloudAnnotationParentGroup>
        {/if}
    {:else if node.cuboid}
        {@render annotationItem(node.cuboid)}
    {/if}
{/snippet}

{#snippet annotationForest(items: readonly CuboidAnnotation[])}
    {#each buildAnnotationForest({ cuboids: items }) as node (forestNodeKey(node))}
        {@render annotationNode(node)}
    {/each}
{/snippet}

{#if cuboids.length === 0}
    <div class="flex h-full items-center justify-center">
        <Typography variant="body2" className="text-muted-foreground">No annotations</Typography>
    </div>
{:else if groups.length <= 1}
    <div class="space-y-1">
        {@render annotationForest(groups[0]?.cuboids ?? [])}
    </div>
{:else}
    <div class="space-y-2">
        {#each groups as group (group.sourceId)}
            <PointCloudAnnotationListGroup name={group.sourceName} count={group.cuboids.length}>
                <div class="space-y-1">
                    {@render annotationForest(group.cuboids)}
                </div>
            </PointCloudAnnotationListGroup>
        {/each}
    </div>
{/if}
