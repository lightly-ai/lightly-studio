<script lang="ts">
    import type {
        AnnotationClass,
        AnnotationSource,
        CuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';
    import {
        groupAnnotationsBySource,
        groupAnnotationsWithEmptySources,
        isPickableSource,
        type SourcePicker,
        resolveAnnotationClassName,
        resolveAnnotationSourceName,
        buildAnnotationForest,
        subtreeContainsId
    } from './pointCloudAnnotationList';
    import { resolveCuboidColor } from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/cuboidColors';
    import PointCloudAnnotationListGroup from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationListGroup';
    import PointCloudAnnotationListItem from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationListItem';
    import PointCloudAnnotationParentGroup from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationList/PointCloudAnnotationParentGroup';
    import { Typography } from '$lib/components/Typography';
    import PointCloudSourcePicker from './PointCloudSourcePicker';

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
        /** Called after the annotation's track assignment changes. */
        onTrackChange?: () => Promise<void>;
        /** Deletes a cuboid annotation by ID. */
        onDeleteCuboid?: (cuboidId: string) => void;
        /** Reloads the tick after a tag of a cuboid is added or removed. */
        onTagsChange?: () => void;
        /** Picks the source for new cuboids. Without it, the list shows no source picker. */
        sourcePicker?: SourcePicker;
        /** True when the cuboid is hidden in the scene. */
        isCuboidHidden?: (cuboid: CuboidAnnotation) => boolean;
        /** True when every cuboid of the source is hidden in the scene. */
        isSourceHidden?: (sourceId: string) => boolean;
        /** Hides or shows the track of a cuboid; row eye buttons are omitted without it. */
        onToggleTrackVisibility?: (cuboid: CuboidAnnotation) => void;
        /** Hides or shows a source; group eye buttons are omitted without it. */
        onToggleSourceVisibility?: (sourceId: string) => void;
    }

    let {
        cuboids,
        annotationClasses,
        annotationSources,
        selectedCuboidId = $bindable(null),
        editable = false,
        onCuboidTransform,
        onLabelChange,
        onTrackChange,
        onDeleteCuboid,
        onTagsChange,
        isCuboidHidden = () => false,
        isSourceHidden = () => false,
        onToggleTrackVisibility,
        onToggleSourceVisibility,
        sourcePicker
    }: Props = $props();

    const groups = $derived(
        sourcePicker
            ? groupAnnotationsWithEmptySources({
                  cuboids,
                  sources: annotationSources,
                  pendingSourceName: sourcePicker.pendingSourceName
              })
            : groupAnnotationsBySource({ cuboids, sources: annotationSources })
    );
    // The group header holds the source toggle, so it shows whenever sources can be toggled,
    // also on a tick with only one source.
    const showGroups = $derived(onToggleSourceVisibility !== undefined || groups.length > 1);
    const occupiedTrackIds = $derived(
        new Set(cuboids.flatMap((c) => (c.trackId ? [c.trackId] : [])))
    );

    function toggle(id: string): void {
        selectedCuboidId = selectedCuboidId === id ? null : id;
    }

    function forestNodeKey(node: AnnotationTreeNode): string {
        if (node.cuboid) return node.cuboid.id;
        const firstChild = node.children[0]?.cuboid;
        if (firstChild?.parentTrackNumber != null) return `absent-${firstChild.parentTrackNumber}`;
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
        {occupiedTrackIds}
        {onCuboidTransform}
        {onLabelChange}
        {onTrackChange}
        onDelete={onDeleteCuboid}
        {onTagsChange}
        isHidden={isCuboidHidden(cuboid)}
        isVisibilityLocked={isSourceHidden(cuboid.annotationSourceId)}
        onToggleVisibility={onToggleTrackVisibility}
    />
{/snippet}

{#snippet childRows(children: readonly AnnotationTreeNode[])}
    {#each children as child, i (child.cuboid?.id ?? child.children[0]?.cuboid?.id)}
        {@const isLast = i === children.length - 1}
        <div class="relative mt-1 pl-4">
            <div class="absolute -top-1 left-2 w-px bg-border {isLast ? 'h-6' : '-bottom-1'}"></div>
            <div class="absolute left-2 top-5 h-px w-2 bg-border"></div>
            {@render annotationNode(child)}
        </div>
    {/each}
{/snippet}

{#snippet annotationNode(node: AnnotationTreeNode)}
    {#if node.cuboid && node.children.length > 0}
        {@render annotationItem(node.cuboid)}
        {@render childRows(node.children)}
    {:else if !node.cuboid && node.children.length > 0}
        {@const firstChild = node.children[0].cuboid}
        {#if firstChild}
            <PointCloudAnnotationParentGroup
                className={firstChild.parentTrackClassName ?? ''}
                trackNumber={firstChild.parentTrackNumber}
                subtreeSize={node.subtreeSize}
                autoExpandForId={selectedCuboidId && subtreeContainsId(node, selectedCuboidId)
                    ? selectedCuboidId
                    : null}
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

{#snippet sourceGroups()}
    <div class="space-y-2">
        {#each groups as group (group.sourceId)}
            <PointCloudAnnotationListGroup
                name={group.sourceName}
                count={group.cuboids.length}
                autoExpandForId={selectedCuboidId &&
                group.cuboids.some((c) => c.id === selectedCuboidId)
                    ? selectedCuboidId
                    : null}
                isTarget={group.sourceName === sourcePicker?.targetSourceName}
                needsPick={sourcePicker?.needsPick}
                onPick={sourcePicker && isPickableSource(group.sourceId, annotationSources)
                    ? () => sourcePicker.onPick(group.sourceName)
                    : undefined}
                isHidden={isSourceHidden(group.sourceId)}
                onToggleVisibility={onToggleSourceVisibility
                    ? () => onToggleSourceVisibility(group.sourceId)
                    : undefined}
            >
                <div class="space-y-1">
                    {#if group.cuboids.length === 0}
                        <Typography variant="body2" className="text-xs text-muted-foreground">
                            No cuboids on this tick
                        </Typography>
                    {:else}
                        {@render annotationForest(group.cuboids)}
                    {/if}
                </div>
            </PointCloudAnnotationListGroup>
        {/each}
    </div>
{/snippet}

{#if sourcePicker}
    <PointCloudSourcePicker
        picker={sourcePicker}
        sourceNames={annotationSources.map(({ name }) => name)}
    >
        {@render sourceGroups()}
    </PointCloudSourcePicker>
{:else if cuboids.length === 0}
    <div class="flex h-full items-center justify-center">
        <Typography variant="body2" className="text-muted-foreground">No annotations</Typography>
    </div>
{:else if !showGroups}
    <div class="space-y-1">
        {@render annotationForest(groups[0]?.cuboids ?? [])}
    </div>
{:else}
    {@render sourceGroups()}
{/if}
